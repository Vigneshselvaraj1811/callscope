import sqlite3

import pytest

import callscope


def test_sqlite_cursor_and_connection_execute():
    conn = sqlite3.connect(":memory:")
    with callscope.scope("test") as s:
        conn.execute("CREATE TABLE users (id INTEGER, name TEXT)")
        conn.executemany("INSERT INTO users VALUES (?, ?)", [(1, "a"), (2, "b")])
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (1,))
        assert cur.fetchall() == [(1, "a")]

    assert [c.target for c in s.calls] == [
        "CREATE TABLE users (id INTEGER, name TEXT)",
        "INSERT INTO users VALUES (?, ?)",
        "SELECT * FROM users WHERE id = ?",
    ]
    assert all(c.kind == "sql" and c.detail["db"] == "sqlite" for c in s.calls)
    assert all(c.scope == "test" for c in s.calls)


def test_location_points_at_user_code():
    conn = sqlite3.connect(":memory:")
    with callscope.scope("t") as s:
        conn.execute("SELECT 1")
    assert s.calls[0].location.startswith("tests/test_sql.py:")
    assert s.calls[0].location.endswith("in test_location_points_at_user_code")


def test_sqlite_custom_factories_keep_working():
    class MyConnection(sqlite3.Connection):
        marker = "conn"

    class MyCursor(sqlite3.Cursor):
        marker = "cursor"

    conn = sqlite3.connect(":memory:", factory=MyConnection)
    assert isinstance(conn, MyConnection)
    with callscope.scope("t") as s:
        cur = conn.cursor(MyCursor)
        assert isinstance(cur, MyCursor)
        cur.execute("SELECT 1")
    assert s.count("sql") == 1


def test_sqlite_errors_are_recorded_and_reraised():
    conn = sqlite3.connect(":memory:")
    with callscope.scope("t") as s, pytest.raises(sqlite3.OperationalError):
        conn.execute("SELECT * FROM nope")
    assert s.calls[0].error.startswith("OperationalError")


def test_uninstall_restores_sqlite3():
    callscope.uninstall()
    with callscope.scope("t") as s:
        sqlite3.connect(":memory:").execute("SELECT 1")
    assert s.count() == 0
    assert not hasattr(sqlite3.connect, "__wrapped__")


def test_sqlalchemy_records_each_query_once():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    engine = sqlalchemy.create_engine("sqlite://")
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("SELECT 1"))  # warm up the pool outside the scope
        with callscope.scope("t") as s:
            conn.execute(sqlalchemy.text("SELECT 2"))
            conn.execute(sqlalchemy.text("SELECT :x"), {"x": 3})
    targets = [c.target for c in s.calls]
    assert targets == ["SELECT 2", "SELECT ?"]
    assert all(c.detail["db"] == "sqlite" for c in s.calls)


def test_sqlalchemy_error():
    sqlalchemy = pytest.importorskip("sqlalchemy")
    engine = sqlalchemy.create_engine("sqlite://")
    with engine.connect() as conn:
        with callscope.scope("t") as s, pytest.raises(sqlalchemy.exc.OperationalError):
            conn.execute(sqlalchemy.text("SELECT * FROM nope"))
        # A failed query must not leave callscope stuck in "active" mode.
        with callscope.scope("t2") as s2:
            conn.execute(sqlalchemy.text("SELECT 1"))
    assert s.count() == 1 and s.calls[0].error
    assert s2.count() == 1
