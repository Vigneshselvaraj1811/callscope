# callscope

**See every HTTP, SQL and Redis call your Python app makes: live, grouped per request, linked to the line of code that made it.**

Think of it as the browser's Network tab, for your backend.

```console
$ callscope run -m uvicorn main:app
  sql   SELECT DISTINCT user_id FROM orders                           0.2ms  <- main.py:19 in load
  sql   SELECT * FROM orders WHERE user_id = ?                        0.1ms  <- main.py:21 in load
  sql   SELECT * FROM orders WHERE user_id = ?                        0.0ms  <- main.py:21 in load
  ...
  http  GET https://api.example.com/rates?token=***                   200  412.3ms  <- main.py:28 in sync_endpoint
* GET /sync -> 200  431ms total, 8 calls (1 http, 7 sql) taking 413ms
  ! n+1  6x same query: SELECT * FROM orders WHERE user_id = ?  <- main.py:21 in load
```

## Why callscope

Most slow endpoints aren't slow because of Python. They make **too many calls**: an N+1 query hidden in a loop, the same API request sent twice, a cache lookup for every row. These bugs are invisible in the code and easy to see in callscope.

<div class="grid" markdown>

- :material-lightning-bolt: **Zero setup.** `pip install pycallscope`, then `callscope run app.py`. No account, no server, no config file.
- :material-puzzle: **Every library, one tool.** `requests`, `httpx`, `sqlite3`, SQLAlchemy, the Django ORM and `redis`, in one stream.
- :material-map-marker: **Points at your code.** Every call shows the line in *your* code that made it, not a line deep inside a library.
- :material-alert: **Finds problems for you.** N+1 queries, duplicate calls and slow calls are flagged per request.
- :material-lock: **Private by default.** Runs locally and sends nothing anywhere. Secrets in URLs are masked, Redis values and SQL parameters are never printed.
- :material-feather: **No dependencies.** Libraries you don't use are skipped.

</div>

## Install

```console
pip install pycallscope
```

Then read [Getting started](getting-started.md).

## Works with

| Kind | Libraries |
|---|---|
| HTTP | `requests`, `httpx` (sync and async) |
| SQL | `sqlite3`, SQLAlchemy (any database), Django ORM |
| Redis | `redis-py` (sync, asyncio, pipelines) |
| Frameworks | FastAPI, Starlette, Flask, Django, any ASGI or WSGI app, plain scripts |

Python 3.9 and newer, on Linux, macOS and Windows.
