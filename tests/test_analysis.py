import io
import sqlite3

import callscope
from callscope import Call, TerminalReporter, analyze, normalize_sql


def _call(kind, target, ms=1.0, location="app.py:1 in f"):
    return Call(kind=kind, target=target, duration_ms=ms, started_at=0.0, location=location)


def test_normalize_sql():
    assert normalize_sql("SELECT * FROM t WHERE id = 1") == normalize_sql(
        "SELECT *  FROM t\nWHERE id = 2"
    )
    assert normalize_sql("SELECT * FROM t WHERE name = 'bob'") == "SELECT * FROM t WHERE name = ?"
    assert (
        normalize_sql("SELECT * FROM t WHERE id IN (1, 2, 3)") == "SELECT * FROM t WHERE id IN (?)"
    )
    assert normalize_sql("SELECT %s, %(x)s, :y, $1") == "SELECT ?, ?, ?, ?"


def test_n_plus_one_detected():
    calls = [_call("sql", f"SELECT * FROM orders WHERE user_id = {i}") for i in range(6)]
    findings = analyze(calls, n_plus_one=5)
    assert [f.kind for f in findings] == ["n+1"]
    assert findings[0].count == 6
    assert findings[0].location == "app.py:1 in f"


def test_below_threshold_is_quiet():
    calls = [_call("sql", f"SELECT * FROM orders WHERE user_id = {i}") for i in range(4)]
    assert analyze(calls, n_plus_one=5) == []


def test_duplicate_and_slow():
    calls = [
        _call("http", "GET https://api.x/users"),
        _call("http", "GET https://api.x/users"),
        _call("redis", "GET k", ms=900),
    ]
    kinds = [f.kind for f in analyze(calls, slow_ms=500)]
    assert kinds == ["duplicate", "slow"]


def test_reporter_end_to_end():
    out = io.StringIO()
    reporter = TerminalReporter(out, n_plus_one=3)
    callscope.add_listener(reporter)
    try:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (id INTEGER)")
        with callscope.scope("GET /orders") as s:
            for i in range(3):
                conn.execute("SELECT * FROM t WHERE id = ?", (i,))
            s.status = 200
    finally:
        callscope.remove_listener(reporter)
    text = out.getvalue()
    assert "SELECT * FROM t WHERE id = ?" in text
    assert "GET /orders -> 200" in text
    assert "3 calls (3 sql)" in text
    assert "n+1" in text and "3x same query" in text
    assert "test_analysis.py" in text


def test_final_summary_covers_unscoped_calls():
    out = io.StringIO()
    reporter = TerminalReporter(out, live=False)
    callscope.add_listener(reporter)
    try:
        sqlite3.connect(":memory:").execute("SELECT 1")
    finally:
        callscope.remove_listener(reporter)
    reporter.print_final_summary()
    assert "callscope summary" in out.getvalue()
    assert "1 calls (1 sql)" in out.getvalue()
