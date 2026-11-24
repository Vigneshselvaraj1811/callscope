"""Find the line in the user's own code that triggered a call."""

from __future__ import annotations

import os
import sys
import sysconfig

_PKG_DIR = os.path.dirname(os.path.abspath(__file__)) + os.sep


def _library_prefixes() -> tuple:
    prefixes = {_PKG_DIR}
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        path = sysconfig.get_paths().get(key)
        if path:
            prefixes.add(os.path.realpath(path) + os.sep)
            prefixes.add(os.path.abspath(path) + os.sep)
    for path in sys.path:
        if path.endswith(("site-packages", "dist-packages")):
            prefixes.add(os.path.realpath(path) + os.sep)
            prefixes.add(os.path.abspath(path) + os.sep)
    return tuple(prefixes)


_LIBRARY_PREFIXES = _library_prefixes()
_cache: dict = {}


def _is_user_file(filename: str) -> bool:
    cached = _cache.get(filename)
    if cached is not None:
        return cached
    if filename.startswith("<"):  # <frozen ...>, <string>
        result = False
    else:
        path = os.path.abspath(filename)
        result = not path.startswith(_LIBRARY_PREFIXES)
    _cache[filename] = result
    return result


def _display_path(filename: str) -> str:
    path = os.path.abspath(filename)
    cwd = os.getcwd() + os.sep
    shown = path[len(cwd) :] if path.startswith(cwd) else path
    return shown.replace(os.sep, "/")


def find_location() -> str | None:
    """Return ``"path/to/file.py:42 in func"`` for the nearest frame in user code."""
    frame = sys._getframe(1)
    while frame is not None:
        filename = frame.f_code.co_filename
        if _is_user_file(filename):
            return f"{_display_path(filename)}:{frame.f_lineno} in {frame.f_code.co_name}"
        frame = frame.f_back
    return None
