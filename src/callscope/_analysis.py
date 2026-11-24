"""Turn a list of calls into findings: N+1 queries, slow calls, duplicate requests."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from ._events import Call

_STRING = re.compile(r"'(?:[^']|'')*'")
_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
# (?<!:) keeps Postgres casts like ``id::text`` intact.
_PLACEHOLDER = re.compile(r"(%s|%\(\w+\)s|(?<!:):\w+|\$\d+|\?)")
_IN_LIST = re.compile(r"\bIN\s*\((?:\s*\?\s*,?)+\)", re.IGNORECASE)
_SPACE = re.compile(r"\s+")


def normalize_sql(sql: str) -> str:
    """Reduce a statement to its shape so ``WHERE id = 1`` and ``WHERE id = 2`` match."""
    text = _STRING.sub("?", sql)
    text = _PLACEHOLDER.sub("?", text)
    text = _NUMBER.sub("?", text)
    text = _IN_LIST.sub("IN (?)", text)
    return _SPACE.sub(" ", text).strip()


@dataclass
class Finding:
    kind: str
    """``"n+1"``, ``"duplicate"`` or ``"slow"``."""
    message: str
    count: int = 1
    location: str | None = None


def _most_common_location(calls: Iterable[Call]) -> str | None:
    locations = Counter(c.location for c in calls if c.location)
    return locations.most_common(1)[0][0] if locations else None


def _short(text: str, width: int = 90) -> str:
    text = _SPACE.sub(" ", text).strip()
    return text if len(text) <= width else text[: width - 3] + "..."


def analyze(calls: Iterable[Call], *, n_plus_one: int = 5, slow_ms: float = 500) -> list:
    """Return a list of :class:`Finding` for the given calls, most important first."""
    calls = list(calls)
    findings: list = []

    by_shape: dict = defaultdict(list)
    for call in calls:
        if call.kind == "sql":
            by_shape[normalize_sql(call.target)].append(call)
    for shape, group in by_shape.items():
        if n_plus_one and len(group) >= n_plus_one:
            findings.append(
                Finding(
                    kind="n+1",
                    message=f"{len(group)}x same query: {_short(shape)}",
                    count=len(group),
                    location=_most_common_location(group),
                )
            )

    by_request: dict = defaultdict(list)
    for call in calls:
        if call.kind in ("http", "redis") and not call.target.startswith("PIPELINE"):
            by_request[(call.kind, call.target)].append(call)
    for (kind, target), group in by_request.items():
        if len(group) >= 2:
            findings.append(
                Finding(
                    kind="duplicate",
                    message=f"{len(group)}x identical {kind} call: {_short(target)}",
                    count=len(group),
                    location=_most_common_location(group),
                )
            )

    if slow_ms:
        for call in calls:
            if call.duration_ms >= slow_ms:
                findings.append(
                    Finding(
                        kind="slow",
                        message=f"{call.duration_ms:.0f}ms {call.kind}: {_short(call.target)}",
                        location=call.location,
                    )
                )

    order = {"n+1": 0, "duplicate": 1, "slow": 2}
    findings.sort(key=lambda f: (order.get(f.kind, 9), -f.count))
    return findings
