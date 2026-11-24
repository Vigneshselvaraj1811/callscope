"""Django ORM, via the official ``connection.execute_wrappers`` hook."""

from __future__ import annotations

from .._events import timed

_installed = False


def _wrapper(execute, sql, params, many, context):
    connection = context.get("connection")
    detail = {"db": getattr(connection, "vendor", "django")}
    if many:
        detail["many"] = True
    return timed("sql", sql, lambda _r: detail, execute, sql, params, many, context)


def _attach(connection) -> None:
    if _wrapper not in connection.execute_wrappers:
        connection.execute_wrappers.append(_wrapper)


def _on_connection_created(sender, connection, **kwargs):
    _attach(connection)


def install() -> bool:
    global _installed
    try:
        from django.db.backends.signals import connection_created
    except ImportError:
        return False
    if _installed:
        return True
    connection_created.connect(_on_connection_created, weak=False, dispatch_uid="callscope")
    # Connections opened before install() won't fire the signal; attach to them now.
    try:
        from django.conf import settings

        if settings.configured:
            from django.db import connections

            for connection in connections.all(initialized_only=True):
                if connection.connection is not None:
                    _attach(connection)
    except Exception:
        pass
    _installed = True
    return True


def uninstall() -> None:
    global _installed
    if not _installed:
        return
    from django.db.backends.signals import connection_created

    connection_created.disconnect(dispatch_uid="callscope")
    try:
        from django.db import connections

        for connection in connections.all(initialized_only=True):
            if _wrapper in connection.execute_wrappers:
                connection.execute_wrappers.remove(_wrapper)
    except Exception:
        pass
    _installed = False
