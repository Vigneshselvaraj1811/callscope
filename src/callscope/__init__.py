"""callscope: see every HTTP, SQL and Redis call your Python app makes.

Quick start::

    import callscope
    callscope.install()

or, with no code changes::

    callscope run app.py
"""

from __future__ import annotations

import atexit
import threading
from collections.abc import Iterable
from typing import TextIO

from ._analysis import Finding, analyze, normalize_sql
from ._events import Call, Listener, Scope, add_listener, current_scope, remove_listener, scope
from ._reporter import TerminalReporter
from .instruments import INSTRUMENTS, KINDS, load

__version__ = "0.1.0"

__all__ = [
    "Call",
    "Finding",
    "Listener",
    "Scope",
    "TerminalReporter",
    "__version__",
    "add_listener",
    "analyze",
    "current_scope",
    "install",
    "installed",
    "normalize_sql",
    "remove_listener",
    "scope",
    "uninstall",
]

_lock = threading.Lock()
_installed: list = []
_reporter: TerminalReporter | None = None
_atexit_registered = False


def _resolve(only: Iterable[str] | None) -> list:
    if only is None:
        return list(INSTRUMENTS)
    names: list = []
    for item in only:
        item = item.strip().lower()
        if item in KINDS:
            names.extend(KINDS[item])
        elif item in INSTRUMENTS:
            names.append(item)
        elif item:
            valid = ", ".join(sorted(set(KINDS) | set(INSTRUMENTS)))
            raise ValueError(f"unknown callscope instrument {item!r}; choose from: {valid}")
    return list(dict.fromkeys(names))


def _final_summary() -> None:
    if _reporter is not None:
        _reporter.print_final_summary()


def install(
    *,
    report: bool = True,
    live: bool = True,
    only: Iterable[str] | None = None,
    slow_ms: float = 500,
    n_plus_one: int = 5,
    stream: TextIO | None = None,
) -> list:
    """Start capturing calls. Safe to call more than once.

    :param report: print calls and summaries to the terminal (stderr by default).
    :param live: print each call as it happens; ``False`` prints only summaries.
    :param only: limit to kinds (``"http"``, ``"sql"``, ``"redis"``) or libraries
        (``"requests"``, ``"httpx"``, ``"sqlite3"``, ``"sqlalchemy"``, ``"django"``, ``"redis"``).
    :param slow_ms: calls at or above this duration are flagged as slow.
    :param n_plus_one: flag a query shape repeated this many times in one request.
    :param stream: where to print; defaults to ``sys.stderr``.
    :returns: names of the libraries that were instrumented.
    """
    global _reporter, _atexit_registered
    with _lock:
        for name in _resolve(only):
            if name not in _installed and load(name).install():
                _installed.append(name)
        if report:
            if _reporter is None:
                _reporter = TerminalReporter(
                    stream, live=live, slow_ms=slow_ms, n_plus_one=n_plus_one
                )
                add_listener(_reporter)
            if not _atexit_registered:
                atexit.register(_final_summary)
                _atexit_registered = True
        return list(_installed)


def uninstall() -> None:
    """Stop capturing and restore every patched library."""
    global _reporter
    with _lock:
        for name in reversed(_installed):
            load(name).uninstall()
        _installed.clear()
        if _reporter is not None:
            remove_listener(_reporter)
            _reporter = None


def installed() -> list:
    """Names of the libraries currently instrumented."""
    return list(_installed)
