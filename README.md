# callscope

[![CI](https://github.com/Vigneshselvaraj1811/callscope/actions/workflows/ci.yml/badge.svg)](https://github.com/Vigneshselvaraj1811/callscope/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pycallscope.svg)](https://pypi.org/project/pycallscope/)
[![Python](https://img.shields.io/pypi/pyversions/pycallscope.svg)](https://pypi.org/project/pycallscope/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**[Documentation](https://vigneshselvaraj1811.github.io/callscope/)** · **[Getting started](https://vigneshselvaraj1811.github.io/callscope/getting-started/)** · **[Changelog](CHANGELOG.md)**

**See every HTTP, SQL and Redis call your Python app makes: live, grouped per request, linked to the line of code that made it.**

Like the browser's Network tab, but for your backend. Zero dependencies, zero config, works with any framework.

```console
$ callscope run app.py
  sql   SELECT * FROM users WHERE active = ?                     0.4ms  <- app.py:12 in list_users
  sql   SELECT * FROM orders WHERE user_id = ?                   0.2ms  <- app.py:15 in list_users
  sql   SELECT * FROM orders WHERE user_id = ?                   0.2ms  <- app.py:15 in list_users
  ...
  http  GET https://api.stripe.com/v1/customers?api_key=***  200  412.9ms  <- billing.py:30 in sync
  redis GET session:42                                           0.1ms  <- auth.py:8 in current_user
* GET /users -> 200  431ms total, 52 calls (1 http, 50 sql, 1 redis) taking 418ms
  ! n+1  49x same query: SELECT * FROM orders WHERE user_id = ?  <- app.py:15 in list_users
```

## Why

Most performance bugs in web apps aren't slow Python. They're **too many calls**: an N+1 query hidden in a loop, the same API request made twice, a cache lookup on every row. callscope shows you each call the moment it happens and tells you which line of *your* code made it.

- **One install, every library:** `requests`, `httpx` (sync and async), `sqlite3`, SQLAlchemy (any database), the Django ORM, and `redis` (sync, async, pipelines).
- **Grouped per request**, with a summary and warnings for **N+1 queries**, **duplicate calls** and **slow calls**.
- **Works with any framework**: FastAPI, Flask, Django, Starlette, plain scripts, workers, tests.
- **Local and private:** nothing is sent anywhere. Secrets in URLs (`token=`, `api_key=`, passwords) are masked, and Redis values are never printed.
- **No dependencies.** If a library isn't installed, callscope skips it.

## Install

```console
pip install pycallscope
```

The package on PyPI is `pycallscope`. You import it as `callscope` and run it as `callscope`.

callscope is a development tool. Keep it in your dev dependencies, not in production.

## Use it

### No code changes

```console
callscope run app.py
callscope run -m uvicorn main:app
callscope run -m flask run
callscope run --only sql -m pytest -x
```

Options: `--quiet` (summaries only), `--only sql,http`, `--slow-ms 200`, `--n-plus-one 3`.

### From code

```python
import callscope

callscope.install()
```

### Group calls per request

Add the middleware for your framework to get a summary and warnings for every request.

**FastAPI / Starlette / any ASGI app**

```python
from callscope.middleware import ASGIMiddleware

app.add_middleware(ASGIMiddleware)
```

**Flask / any WSGI app**

```python
from callscope.middleware import WSGIMiddleware

app.wsgi_app = WSGIMiddleware(app.wsgi_app)
```

**Django** (put it first in `MIDDLEWARE`)

```python
MIDDLEWARE = ["callscope.middleware.DjangoMiddleware", ...]
```

### Group any block of code

```python
with callscope.scope("nightly import") as s:
    run_import()

print(s.count("sql"), s.counts())
```

### Catch N+1 queries in your tests

```python
import callscope


def test_user_list_is_not_n_plus_one(client):
    callscope.install(report=False)
    with callscope.scope("GET /users") as s:
        client.get("/users")
    assert s.count("sql") <= 3
```

### Send calls anywhere

```python
class SlowCallLogger(callscope.Listener):
    def on_call(self, call):
        if call.duration_ms > 1000:
            log.warning("slow %s %s at %s", call.kind, call.target, call.location)


callscope.add_listener(SlowCallLogger())
```

## What gets captured

| Kind | Libraries | Shown |
|---|---|---|
| `http` | `requests`, `httpx` (sync and async) | Method, URL (secrets masked), status, duration |
| `sql` | `sqlite3`, SQLAlchemy, Django ORM | Statement (parameters are not printed), database, duration |
| `redis` | `redis-py` (sync, asyncio, pipelines) | Command and key only, never values |

Each call also records the line in your code that triggered it, and any error raised.

## Notes and limits

- With `uvicorn --reload` or Django's autoreloader, the server runs in a child process. Use `callscope.install()` in your app code (or run without reload) so the child is instrumented.
- `WSGIMiddleware` reads the whole response body inside the request so that calls made while streaming are counted. Don't use it for large streaming downloads.
- Calls in threads you start yourself are grouped with a request only if the thread runs in a copy of the request's context (`contextvars.copy_context()`). FastAPI's sync endpoints already do this.

## Roadmap

- Browser dashboard with a live timeline
- `psycopg`, `asyncpg`, `aiohttp`, `pymongo`, Celery
- pytest plugin: `assert_max_queries` fixture and N+1 failures in CI

## Contributing

Bug reports, ideas and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) to get started, and please report security issues privately as described in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © Vignesh Selvaraj
