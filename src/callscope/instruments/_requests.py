from __future__ import annotations

from .._events import timed
from .._redact import redact_url

_original = None


def _status(response) -> dict:
    return {"status": response.status_code}


def install() -> bool:
    global _original
    try:
        import requests
    except ImportError:
        return False
    if _original is not None:
        return True
    _original = original = requests.Session.send

    def send(self, request, **kwargs):
        target = f"{request.method} {redact_url(str(request.url))}"
        return timed("http", target, _status, original, self, request, **kwargs)

    send.__wrapped__ = original  # type: ignore[attr-defined]
    requests.Session.send = send
    return True


def uninstall() -> None:
    global _original
    if _original is None:
        return
    import requests

    requests.Session.send = _original
    _original = None
