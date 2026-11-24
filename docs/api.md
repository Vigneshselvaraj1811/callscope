# Python API

Everything below is importable from the top-level `callscope` package.

## `callscope.install`

```python
callscope.install(
    *,
    report: bool = True,
    live: bool = True,
    only: Iterable[str] | None = None,
    slow_ms: float = 500,
    n_plus_one: int = 5,
    stream: TextIO | None = None,
) -> list[str]
```

Start capturing calls. Safe to call more than once: later calls don't patch anything twice.

| Parameter | Description |
|---|---|
| `report` | Print calls and summaries to the terminal. Use `False` in tests or when you only want [listeners](#callscopelistener). |
| `live` | Print each call as it happens. `False` prints only summaries. |
| `only` | Limit capture to kinds (`"http"`, `"sql"`, `"redis"`) or libraries (`"requests"`, `"httpx"`, `"sqlite3"`, `"sqlalchemy"`, `"django"`, `"redis"`). Raises `ValueError` for unknown names. |
| `slow_ms` | Flag calls at or above this duration. `0` turns the check off. |
| `n_plus_one` | Flag a query shape repeated this many times in one scope. `0` turns the check off. |
| `stream` | Where to print. Defaults to `sys.stderr`. |

**Returns** the names of the libraries that were instrumented. Libraries that aren't installed are skipped.

```python
>>> callscope.install(report=False)
['requests', 'httpx', 'sqlite3', 'sqlalchemy', 'redis']
```

## `callscope.uninstall`

```python
callscope.uninstall() -> None
```

Stop capturing, restore every patched library and remove the terminal reporter.

## `callscope.installed`

```python
callscope.installed() -> list[str]
```

Names of the libraries currently instrumented.

## `callscope.scope`

```python
with callscope.scope(name: str) as s:
    ...
```

Group every call made inside the block under `name`, and yield a [`Scope`](#callscopescope_1). When the block ends, listeners receive `on_scope_end` and the terminal reporter prints a summary.

Scopes follow `contextvars`, so they work across `await` and in thread pools that copy the context. A scope started inside a tracked call (for example an app served in-process by a test client) still records its own calls.

## `callscope.Scope`

| Attribute / method | Description |
|---|---|
| `name: str` | The name given to `scope()`, or `"METHOD /path"` from middleware. |
| `calls: list[Call]` | Calls made inside the scope, in order. |
| `status: int \| None` | HTTP status code, set by the middleware. |
| `started_at: float` | Unix timestamp. |
| `duration_ms: float \| None` | Total duration, set when the scope ends. |
| `count(kind=None) -> int` | Number of calls, optionally of one kind. |
| `counts() -> dict[str, int]` | Calls per kind, e.g. `{"sql": 12, "http": 1}`. |

## `callscope.current_scope`

```python
callscope.current_scope() -> Scope | None
```

The innermost active scope, if any.

## `callscope.Call`

One recorded call.

| Attribute | Description |
|---|---|
| `kind: str` | `"http"`, `"sql"` or `"redis"`. |
| `target: str` | `"GET https://..."` (secrets masked), the SQL statement, or `"GET key"` / `"PIPELINE[3] SET, INCRBY, GET"`. |
| `duration_ms: float` | How long the call took. |
| `started_at: float` | Unix timestamp. |
| `location: str \| None` | The line in your code that made the call, e.g. `"app/views.py:42 in list_users"`. |
| `error: str \| None` | `"ExceptionType: message"` if the call raised. The exception is always re-raised to your code. |
| `detail: dict` | Extra facts: `status` for HTTP, `db` for SQL (`"sqlite"`, `"postgresql"`...), `many` for `executemany`. |
| `scope: str \| None` | Name of the scope the call belongs to. |

## `callscope.Listener`

Subclass and override what you need, then register it with `add_listener`. Exceptions raised in a listener are swallowed, so a broken listener can never break your app.

```python
class SlowCallLogger(callscope.Listener):
    def on_call(self, call: callscope.Call) -> None:
        if call.duration_ms > 1000:
            log.warning("slow %s %s at %s", call.kind, call.target, call.location)

    def on_scope_end(self, scope: callscope.Scope) -> None:
        if scope.count("sql") > 50:
            log.warning("%s made %d queries", scope.name, scope.count("sql"))


callscope.install(report=False)
callscope.add_listener(SlowCallLogger())
```

Listeners are called on the thread that made the call. Keep them fast.

## `callscope.add_listener` / `callscope.remove_listener`

```python
callscope.add_listener(listener: Listener) -> None
callscope.remove_listener(listener: Listener) -> None
```

## `callscope.analyze`

```python
callscope.analyze(calls, *, n_plus_one: int = 5, slow_ms: float = 500) -> list[Finding]
```

Check a list of calls for N+1 queries, duplicate calls and slow calls. Returns findings ordered by importance (N+1 first). See [Findings explained](findings.md).

## `callscope.Finding`

| Attribute | Description |
|---|---|
| `kind: str` | `"n+1"`, `"duplicate"` or `"slow"`. |
| `message: str` | Human-readable description. |
| `count: int` | How many calls are involved. |
| `location: str \| None` | The line most responsible. |

## `callscope.normalize_sql`

```python
callscope.normalize_sql(sql: str) -> str
```

Reduce a statement to its shape: literals and placeholders (`?`, `%s`, `%(name)s`, `:name`, `$1`) become `?`, `IN (...)` lists collapse, whitespace is normalized.

```python
>>> callscope.normalize_sql("SELECT * FROM t WHERE id IN (1, 2, 3) AND name = 'bob'")
'SELECT * FROM t WHERE id IN (?) AND name = ?'
```

## `callscope.TerminalReporter`

The listener behind the terminal output. Use it directly to print to a different stream or with different thresholds:

```python
import io

buffer = io.StringIO()
reporter = callscope.TerminalReporter(buffer, live=False, slow_ms=200, n_plus_one=3)
callscope.install(report=False)
callscope.add_listener(reporter)
```

## Middleware

See [Frameworks](frameworks.md).

| Class | For |
|---|---|
| `callscope.middleware.ASGIMiddleware` | FastAPI, Starlette, any ASGI app |
| `callscope.middleware.WSGIMiddleware` | Flask, any WSGI app |
| `callscope.middleware.DjangoMiddleware` | Django (sync) |
