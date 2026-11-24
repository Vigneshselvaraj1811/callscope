"""Core data model: a recorded call, a request scope, and the recorder that ties them together."""

from __future__ import annotations

import contextvars
import threading
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable

from ._callsite import find_location


@dataclass
class Call:
    """One outgoing call made by the application."""

    kind: str
    """``"http"``, ``"sql"`` or ``"redis"``."""
    target: str
    """What was called, e.g. ``"GET https://api.example.com/users"`` or the SQL statement."""
    duration_ms: float
    started_at: float
    """Unix timestamp."""
    location: str | None = None
    """The line in *your* code that triggered the call, e.g. ``"app/views.py:42 in list_users"``."""
    error: str | None = None
    detail: dict = field(default_factory=dict)
    """Extra facts such as ``{"status": 200}`` or ``{"db": "sqlite"}``."""
    scope: str | None = None
    """Name of the request (or user scope) this call belongs to."""


@dataclass
class Scope:
    """A unit of work, usually one incoming request, that groups the calls made during it."""

    name: str
    started_at: float = field(default_factory=time.time)
    duration_ms: float | None = None
    status: int | None = None
    calls: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def _add(self, call: Call) -> None:
        with self._lock:
            self.calls.append(call)

    def count(self, kind: str | None = None) -> int:
        """Number of calls, optionally only of one kind (``"http"``, ``"sql"``, ``"redis"``)."""
        with self._lock:
            if kind is None:
                return len(self.calls)
            return sum(1 for c in self.calls if c.kind == kind)

    def counts(self) -> dict:
        with self._lock:
            return dict(Counter(c.kind for c in self.calls))


class Listener:
    """Receives events. Subclass it, override what you need, then call ``add_listener``."""

    def on_call(self, call: Call) -> None:  # pragma: no cover - default no-op
        pass

    def on_scope_end(self, scope: Scope) -> None:  # pragma: no cover - default no-op
        pass


_current_scope: contextvars.ContextVar[Scope | None] = contextvars.ContextVar(
    "callscope_scope", default=None
)
# True while a call is being tracked. Nested calls (e.g. SQLAlchemy -> sqlite3, or
# requests following a redirect) are not recorded twice.
_active: contextvars.ContextVar[bool] = contextvars.ContextVar("callscope_active", default=False)

_listeners: list = []
_listeners_lock = threading.Lock()


def add_listener(listener: Listener) -> None:
    with _listeners_lock:
        if listener not in _listeners:
            _listeners.append(listener)


def remove_listener(listener: Listener) -> None:
    with _listeners_lock:
        if listener in _listeners:
            _listeners.remove(listener)


def _snapshot_listeners() -> list:
    with _listeners_lock:
        return list(_listeners)


def emit(call: Call) -> None:
    current = _current_scope.get()
    if current is not None:
        call.scope = current.name
        current._add(call)
    for listener in _snapshot_listeners():
        try:
            listener.on_call(call)
        except Exception:  # a broken listener must never break the user's app
            pass


@contextmanager
def scope(name: str) -> Iterator[Scope]:
    """Group every call made inside the ``with`` block under ``name``.

    >>> with callscope.scope("import users") as s:
    ...     run_import()
    >>> s.count("sql")
    """
    s = Scope(name=name)
    token = _current_scope.set(s)
    # A scope is a new unit of work. If it starts inside a tracked call (e.g. an
    # in-process app served through FastAPI's TestClient, whose httpx request is
    # being tracked), calls inside the scope must still be recorded.
    active_token = _active.set(False)
    start = time.perf_counter()
    try:
        yield s
    finally:
        s.duration_ms = (time.perf_counter() - start) * 1000
        try:
            _active.reset(active_token)
        except ValueError:  # scope ended in a different context
            pass
        _current_scope.reset(token)
        for listener in _snapshot_listeners():
            try:
                listener.on_scope_end(s)
            except Exception:
                pass


def current_scope() -> Scope | None:
    return _current_scope.get()


class _Pending:
    __slots__ = ("kind", "target", "location", "start", "started_at", "token")

    def __init__(self, kind: str, target: str, token: contextvars.Token) -> None:
        self.kind = kind
        self.target = target
        self.location = find_location()
        self.token = token
        self.started_at = time.time()
        self.start = time.perf_counter()


def begin(kind: str, target: str) -> _Pending | None:
    """Start tracking a call. Returns ``None`` if we're already inside a tracked call."""
    if _active.get():
        return None
    return _Pending(kind, target, _active.set(True))


def finish(
    pending: _Pending | None, error: BaseException | None = None, detail: dict | None = None
) -> None:
    if pending is None:
        return
    duration_ms = (time.perf_counter() - pending.start) * 1000
    try:
        _active.reset(pending.token)
    except ValueError:  # token from another context (e.g. greenlet hop)
        _active.set(False)
    emit(
        Call(
            kind=pending.kind,
            target=pending.target,
            duration_ms=duration_ms,
            started_at=pending.started_at,
            location=pending.location,
            error=f"{type(error).__name__}: {error}" if error is not None else None,
            detail=detail or {},
        )
    )


def _safe_detail(on_result: Callable[[Any], dict] | None, result: Any) -> dict:
    if on_result is None:
        return {}
    try:
        return on_result(result) or {}
    except Exception:
        return {}


def timed(
    kind: str,
    target: str,
    on_result: Callable[[Any], dict] | None,
    fn: Callable,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Run ``fn(*args, **kwargs)`` and record it as a call."""
    pending = begin(kind, target)
    if pending is None:
        return fn(*args, **kwargs)
    try:
        result = fn(*args, **kwargs)
    except BaseException as exc:
        finish(pending, error=exc)
        raise
    finish(pending, detail=_safe_detail(on_result, result))
    return result


async def atimed(
    kind: str,
    target: str,
    on_result: Callable[[Any], dict] | None,
    fn: Callable,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Async version of :func:`timed`."""
    pending = begin(kind, target)
    if pending is None:
        return await fn(*args, **kwargs)
    try:
        result = await fn(*args, **kwargs)
    except BaseException as exc:
        finish(pending, error=exc)
        raise
    finish(pending, detail=_safe_detail(on_result, result))
    return result
