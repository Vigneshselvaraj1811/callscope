"""Instrumentations. Each module exposes ``install() -> bool`` and ``uninstall() -> None``.

``install`` returns ``False`` when the library isn't installed, so callscope never
adds a dependency or crashes because something is missing.
"""

from __future__ import annotations

import importlib

# name -> module path (relative to this package)
INSTRUMENTS = {
    "requests": "._requests",
    "httpx": "._httpx",
    "sqlite3": "._sqlite3",
    "sqlalchemy": "._sqlalchemy",
    "django": "._django",
    "redis": "._redis",
}

KINDS = {
    "http": ("requests", "httpx"),
    "sql": ("sqlite3", "sqlalchemy", "django"),
    "redis": ("redis",),
}


def load(name: str):
    return importlib.import_module(INSTRUMENTS[name], __name__)
