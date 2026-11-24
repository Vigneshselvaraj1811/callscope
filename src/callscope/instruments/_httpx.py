from __future__ import annotations

from .._events import atimed, timed
from .._redact import redact_url

_originals: dict = {}


def _status(response) -> dict:
    return {"status": response.status_code}


def _target(request) -> str:
    return f"{request.method} {redact_url(str(request.url))}"


def install() -> bool:
    try:
        import httpx
    except ImportError:
        return False
    if _originals:
        return True
    sync_send = _originals["Client"] = httpx.Client.send
    async_send = _originals["AsyncClient"] = httpx.AsyncClient.send

    def send(self, request, **kwargs):
        return timed("http", _target(request), _status, sync_send, self, request, **kwargs)

    async def asend(self, request, **kwargs):
        return await atimed("http", _target(request), _status, async_send, self, request, **kwargs)

    send.__wrapped__ = sync_send  # type: ignore[attr-defined]
    asend.__wrapped__ = async_send  # type: ignore[attr-defined]
    httpx.Client.send = send
    httpx.AsyncClient.send = asend
    return True


def uninstall() -> None:
    if not _originals:
        return
    import httpx

    httpx.Client.send = _originals.pop("Client")
    httpx.AsyncClient.send = _originals.pop("AsyncClient")
