"""Print calls and per-request summaries to the terminal."""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import TextIO

from ._analysis import analyze
from ._events import Call, Listener, Scope

_KIND_COLORS = {"http": "36", "sql": "35", "redis": "31"}


def _use_color(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and stream.isatty()


class TerminalReporter(Listener):
    def __init__(
        self,
        stream: TextIO | None = None,
        *,
        live: bool = True,
        slow_ms: float = 500,
        n_plus_one: int = 5,
        width: int = 100,
    ) -> None:
        self._stream = stream
        self.live = live
        self.slow_ms = slow_ms
        self.n_plus_one = n_plus_one
        self.width = width
        self._lock = threading.Lock()
        self._unscoped: list = []
        self._started = time.time()

    @property
    def stream(self) -> TextIO:
        return self._stream if self._stream is not None else sys.stderr

    def _c(self, text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if _use_color(self.stream) else text

    def _write(self, line: str) -> None:
        with self._lock:
            try:
                self.stream.write(line + "\n")
                self.stream.flush()
            except Exception:
                pass

    def _format_call(self, call: Call) -> str:
        kind = self._c(f"{call.kind:<5}", _KIND_COLORS.get(call.kind, "0"))
        target = " ".join(call.target.split())
        if len(target) > self.width:
            target = target[: self.width - 3] + "..."
        parts = [f"  {kind} {target:<60}"]
        status = call.detail.get("status")
        if status is not None:
            parts.append(self._c(str(status), "32" if status < 400 else "31"))
        duration = f"{call.duration_ms:.1f}ms"
        parts.append(self._c(duration, "33") if call.duration_ms >= self.slow_ms else duration)
        if call.error:
            parts.append(self._c(f"! {call.error}", "31"))
        if call.location:
            parts.append(self._c(f"<- {call.location}", "2"))
        return "  ".join(parts)

    def on_call(self, call: Call) -> None:
        if call.scope is None:
            with self._lock:
                self._unscoped.append(call)
        if self.live:
            self._write(self._format_call(call))

    def _summary(self, title: str, calls: list, duration_ms: float | None) -> list:
        counts: dict = {}
        for call in calls:
            counts[call.kind] = counts.get(call.kind, 0) + 1
        breakdown = ", ".join(f"{n} {k}" for k, n in sorted(counts.items()))
        total = sum(c.duration_ms for c in calls)
        timing = f"{duration_ms:.0f}ms total, " if duration_ms is not None else ""
        lines = [
            f"{self._c('*', '1;34')} {self._c(title, '1')}  {timing}"
            f"{len(calls)} calls ({breakdown or 'none'}) taking {total:.0f}ms"
        ]
        for finding in analyze(calls, n_plus_one=self.n_plus_one, slow_ms=self.slow_ms):
            where = f"  {self._c('<- ' + finding.location, '2')}" if finding.location else ""
            lines.append(f"  {self._c('! ' + finding.kind, '1;33')}  {finding.message}{where}")
        return lines

    def on_scope_end(self, scope: Scope) -> None:
        title = scope.name if scope.status is None else f"{scope.name} -> {scope.status}"
        with scope._lock:
            calls = list(scope.calls)
        for line in self._summary(title, calls, scope.duration_ms):
            self._write(line)

    def print_final_summary(self) -> None:
        """Summarize calls made outside any request scope (e.g. in a plain script)."""
        with self._lock:
            calls, self._unscoped = self._unscoped, []
        if not calls:
            return
        elapsed = (time.time() - self._started) * 1000
        for line in self._summary("callscope summary", calls, elapsed):
            self._write(line)
