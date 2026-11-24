# Changelog

## 0.1.0 (2026-11-24)

First release.

- Capture HTTP calls from `requests` and `httpx` (sync and async).
- Capture SQL from `sqlite3`, SQLAlchemy and the Django ORM.
- Capture Redis commands and pipelines from `redis-py` (sync and asyncio).
- Show the line of user code that made each call.
- Group calls per request with ASGI, WSGI and Django middleware, or `callscope.scope()`.
- Detect N+1 queries, duplicate calls and slow calls.
- `callscope run` CLI to use it with no code changes.
- Mask secrets in URLs, never print Redis values or SQL parameters.
