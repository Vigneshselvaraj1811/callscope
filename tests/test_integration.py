import asyncio
import os
import sqlite3
import subprocess
import sys
import textwrap
import threading

import pytest

import callscope
from callscope.middleware import ASGIMiddleware, WSGIMiddleware


def test_install_is_idempotent_and_reports_libraries():
    first = callscope.install(report=False)
    second = callscope.install(report=False)
    assert first == second
    assert "sqlite3" in first


def test_install_only_and_unknown_name():
    callscope.uninstall()
    assert callscope.install(report=False, only=["sql"]) == [
        name for name in ("sqlite3", "sqlalchemy", "django") if name in callscope.installed()
    ]
    with pytest.raises(ValueError):
        callscope.install(report=False, only=["mongo"])


def test_scope_is_shared_with_threadpool_via_context_copy():
    import contextvars

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    with callscope.scope("t") as s:
        ctx = contextvars.copy_context()
        t = threading.Thread(target=ctx.run, args=(conn.execute, "SELECT 1"))
        t.start()
        t.join()
    assert s.count() == 1


def test_asgi_middleware_groups_calls_per_request():
    conn = sqlite3.connect(":memory:")
    ended = []

    class Collect(callscope.Listener):
        def on_scope_end(self, scope):
            ended.append(scope)

    async def app(scope, receive, send):
        conn.execute("SELECT 1")
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def send(message):
        pass

    listener = Collect()
    callscope.add_listener(listener)
    try:
        asyncio.run(
            ASGIMiddleware(app)({"type": "http", "method": "POST", "path": "/x"}, None, send)
        )
    finally:
        callscope.remove_listener(listener)
    assert ended[0].name == "POST /x"
    assert ended[0].status == 201
    assert ended[0].count("sql") == 1


def test_wsgi_middleware_groups_calls_per_request():
    conn = sqlite3.connect(":memory:")
    ended = []

    class Collect(callscope.Listener):
        def on_scope_end(self, scope):
            ended.append(scope)

    def app(environ, start_response):
        start_response("404 Not Found", [])
        yield conn.execute("SELECT 1") and b"body"  # call made while streaming

    listener = Collect()
    callscope.add_listener(listener)
    try:
        body = WSGIMiddleware(app)({"REQUEST_METHOD": "GET", "PATH_INFO": "/y"}, lambda *a: None)
    finally:
        callscope.remove_listener(listener)
    assert body == [b"body"]
    assert (ended[0].name, ended[0].status, ended[0].count()) == ("GET /y", 404, 1)


def test_cli_runs_a_script(tmp_path):
    script = tmp_path / "demo.py"
    script.write_text(
        textwrap.dedent(
            """
            import sqlite3, sys
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE t (id INTEGER)")
            for i in range(6):
                conn.execute("SELECT * FROM t WHERE id = ?", (i,))
            print("argv", sys.argv[1:])
            """
        )
    )
    env = {**os.environ, "NO_COLOR": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "callscope", "run", str(script), "--flag", "x"],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "argv ['--flag', 'x']" in result.stdout
    assert "CREATE TABLE t" in result.stderr
    assert "demo.py:" in result.stderr
    assert "callscope summary" in result.stderr
    assert "6x same query" in result.stderr


def test_cli_passes_options_after_module_to_the_program(tmp_path):
    (tmp_path / "mymod.py").write_text("import sys; print('argv', sys.argv[1:])")
    result = subprocess.run(
        [sys.executable, "-m", "callscope", "run", "--quiet", "-m", "mymod", "-x", "--quiet"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "argv ['-x', '--quiet']" in result.stdout


def test_cli_help_and_errors():
    from callscope.cli import main

    assert main(["--help"]) == 0
    assert main(["--version"]) == 0
    assert main(["nope"]) == 2
    assert main(["run"]) == 2
    assert main(["run", "does_not_exist.py"]) == 2
