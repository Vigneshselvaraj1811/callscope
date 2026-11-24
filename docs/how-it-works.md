# How it works

callscope is about 1,300 lines of plain Python with no dependencies. This page explains the design, for the curious and for contributors.

## The pipeline

```text
your code ──> library call ──> instrument ──> Call ──> current Scope
                                                  └──> listeners ──> terminal / your code
```

1. An **instrument** wraps one library's lowest public entry point (for example `requests.Session.send`).
2. When your code makes a call, the wrapper times it, finds the line in your code that triggered it, and builds a `Call`.
3. The call is added to the **current scope** (one request) and passed to every **listener**.
4. When a scope ends, listeners get the whole scope. The terminal reporter runs [`analyze()`](findings.md) and prints the summary.

## Instruments

Each instrument patches the narrowest point that sees every call, and restores the original on `uninstall()`.

| Library | Hook | Why there |
|---|---|---|
| `requests` | `Session.send` | Every `requests.get()`, `Session.get()` and adapter call goes through it. |
| `httpx` | `Client.send`, `AsyncClient.send` | Same, for sync and async clients. |
| `sqlite3` | `sqlite3.connect` hands out `Connection` / `Cursor` subclasses | The classes are written in C and can't be patched directly. Custom `factory=` classes are kept by combining them with callscope's. |
| SQLAlchemy | `before_cursor_execute` / `after_cursor_execute` / `handle_error` engine events | Official API, works for every dialect. |
| Django ORM | `connection.execute_wrappers` | Official API, works for every backend. |
| `redis` | `Redis.execute_command`, `Pipeline.execute` (+ asyncio versions) | Every command and pipeline goes through these. |

An instrument whose library isn't installed returns `False` from `install()` and is skipped. Nothing is imported unless it's already installed.

## No double counting

Libraries call each other: SQLAlchemy and Django on SQLite both end up in `sqlite3`, and `requests` calls `send` again to follow redirects. A context variable marks "a call is being tracked", and nested calls inside it are not recorded again. So you see one line per query, from the highest-level library.

A new scope resets that marker. That matters for test clients: FastAPI's `TestClient` sends its request through `httpx` (which is tracked) and runs the app in-process, and the app's own calls must still be recorded.

## Finding your line of code

For each call, callscope walks up the stack and stops at the first frame that is not in:

- callscope itself,
- the standard library,
- `site-packages` / `dist-packages`.

That frame is your code. Its path is shown relative to the current directory. Results are cached per file, so the walk is cheap.

## Scopes and concurrency

The current scope lives in a `contextvars.ContextVar`. That makes grouping correct for:

- concurrent `asyncio` requests (each task has its own context),
- thread pools that copy the context (FastAPI / Starlette sync endpoints, `asyncio.to_thread`),
- nested scopes (the inner one wins until it ends).

Adding a call to a scope is guarded by a lock, so threads sharing a scope are safe.

## Overhead

Each call costs a few microseconds: a stack walk (usually cached), two `perf_counter()` calls and one object. That's negligible next to a network round trip or a database query, but callscope is still meant for development, not production.
