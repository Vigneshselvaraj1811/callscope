"""sqlite3 is a C extension, so we can't patch its methods. Instead we wrap
``sqlite3.connect`` to hand out instrumented Connection/Cursor subclasses."""

from __future__ import annotations

import sqlite3

from .._events import timed

_DETAIL = {"db": "sqlite"}
_original_connect = None
_class_cache: dict = {}


def _detail(_result) -> dict:
    return _DETAIL


class _CursorMixin:
    def execute(self, sql, parameters=(), /):
        return timed("sql", sql, _detail, super().execute, sql, parameters)

    def executemany(self, sql, seq_of_parameters, /):
        return timed("sql", sql, _detail, super().executemany, sql, seq_of_parameters)

    def executescript(self, sql_script, /):
        return timed("sql", sql_script, _detail, super().executescript, sql_script)


def _instrumented(base: type, mixin: type) -> type:
    if issubclass(base, mixin):
        return base
    cls = _class_cache.get((base, mixin))
    if cls is None:
        cls = type(f"Callscope{base.__name__}", (mixin, base), {})
        _class_cache[(base, mixin)] = cls
    return cls


class _ConnectionMixin:
    def cursor(self, factory=None):
        return super().cursor(_instrumented(factory or sqlite3.Cursor, _CursorMixin))

    # The C implementations of these bypass our cursor() override, so route them
    # through an instrumented cursor explicitly (same return value: the cursor).
    def execute(self, sql, parameters=(), /):
        return self.cursor().execute(sql, parameters)

    def executemany(self, sql, seq_of_parameters, /):
        return self.cursor().executemany(sql, seq_of_parameters)

    def executescript(self, sql_script, /):
        return self.cursor().executescript(sql_script)


# connect(database, timeout, detect_types, isolation_level, check_same_thread, factory, ...)
_FACTORY_POSITION = 5


def install() -> bool:
    global _original_connect
    if _original_connect is not None:
        return True
    _original_connect = original = sqlite3.connect

    def connect(*args, **kwargs):
        if len(args) > _FACTORY_POSITION:
            args = list(args)
            args[_FACTORY_POSITION] = _instrumented(args[_FACTORY_POSITION], _ConnectionMixin)
        else:
            base = kwargs.get("factory") or sqlite3.Connection
            kwargs["factory"] = _instrumented(base, _ConnectionMixin)
        return original(*args, **kwargs)

    connect.__wrapped__ = original  # type: ignore[attr-defined]
    connect.__doc__ = original.__doc__
    sqlite3.connect = connect
    return True


def uninstall() -> None:
    global _original_connect
    if _original_connect is None:
        return
    sqlite3.connect = _original_connect
    _original_connect = None
