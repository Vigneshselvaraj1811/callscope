"""SQLAlchemy (any database it supports), via engine-wide cursor events."""

from __future__ import annotations

from .._events import begin, finish

_ATTR = "_callscope_pending"
_installed = False


def _before(conn, cursor, statement, parameters, context, executemany):
    if context is not None:
        setattr(context, _ATTR, begin("sql", statement))


def _after(conn, cursor, statement, parameters, context, executemany):
    pending = getattr(context, _ATTR, None) if context is not None else None
    if pending is not None:
        setattr(context, _ATTR, None)
        detail = {"db": conn.dialect.name}
        if executemany:
            detail["many"] = True
        finish(pending, detail=detail)


def _error(exception_context):
    context = exception_context.execution_context
    pending = getattr(context, _ATTR, None) if context is not None else None
    if pending is not None:
        setattr(context, _ATTR, None)
        finish(pending, error=exception_context.original_exception)


def install() -> bool:
    global _installed
    try:
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
    except ImportError:
        return False
    if _installed:
        return True
    event.listen(Engine, "before_cursor_execute", _before)
    event.listen(Engine, "after_cursor_execute", _after)
    event.listen(Engine, "handle_error", _error)
    _installed = True
    return True


def uninstall() -> None:
    global _installed
    if not _installed:
        return
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    event.remove(Engine, "before_cursor_execute", _before)
    event.remove(Engine, "after_cursor_execute", _after)
    event.remove(Engine, "handle_error", _error)
    _installed = False
