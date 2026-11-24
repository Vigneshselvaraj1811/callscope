import asyncio

import pytest

import callscope
from callscope._redact import redact_url


def test_requests(http_server):
    requests = pytest.importorskip("requests")
    with callscope.scope("t") as s:
        assert requests.get(f"{http_server}/users").status_code == 200
        requests.get(f"{http_server}/missing")
    assert [c.target for c in s.calls] == [
        f"GET {http_server}/users",
        f"GET {http_server}/missing",
    ]
    assert [c.detail["status"] for c in s.calls] == [200, 404]
    assert s.calls[0].location.startswith("tests/test_http.py:")


def test_requests_connection_error_is_recorded():
    requests = pytest.importorskip("requests")
    with callscope.scope("t") as s, pytest.raises(requests.ConnectionError):
        requests.get("http://127.0.0.1:9/", timeout=1)
    # Refused on Linux/macOS, times out on Windows; both must be recorded.
    assert s.calls[0].error.startswith(("ConnectionError", "ConnectTimeout"))


def test_httpx_sync(http_server):
    httpx = pytest.importorskip("httpx")
    with callscope.scope("t") as s, httpx.Client() as client:
        client.get(f"{http_server}/a")
    assert s.calls[0].target == f"GET {http_server}/a"
    assert s.calls[0].detail["status"] == 200


def test_httpx_async(http_server):
    httpx = pytest.importorskip("httpx")

    async def main():
        with callscope.scope("t") as s:
            async with httpx.AsyncClient() as client:
                await asyncio.gather(client.get(f"{http_server}/a"), client.get(f"{http_server}/b"))
        return s

    s = asyncio.run(main())
    assert sorted(c.target for c in s.calls) == [f"GET {http_server}/a", f"GET {http_server}/b"]


def test_secrets_are_redacted(http_server):
    requests = pytest.importorskip("requests")
    with callscope.scope("t") as s:
        requests.get(f"{http_server}/x", params={"api_key": "SECRET123", "page": "2"})
    assert "SECRET123" not in s.calls[0].target
    assert "page=2" in s.calls[0].target


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://u:pw@host/p", "https://u:***@host/p"),
        ("https://h/p?token=abc&q=1", "https://h/p?token=***&q=1"),
        ("https://h/p?Password=x", "https://h/p?Password=***"),
        ("https://h/p?q=1", "https://h/p?q=1"),
    ],
)
def test_redact_url(url, expected):
    assert redact_url(url) == expected
