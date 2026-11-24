# FAQ and troubleshooting

## I don't see any output

- **Is the server running with a reloader?** `uvicorn --reload`, `flask run --debug` and Django's `runserver` (without `--noreload`) serve requests from a child process that `callscope run` doesn't reach. Turn the reloader off, or call `callscope.install()` in your app code.
- **Is the library supported?** See the [list](index.md#works-with). Clients like `aiohttp`, `urllib`, `psycopg` without SQLAlchemy or Django, and `pymongo` aren't captured yet.
- **Did you pass `report=False`?** Then nothing is printed. Use a listener or read the scope.
- **Is the connection older than `install()`?** `sqlite3` connections opened before `install()` aren't instrumented. Call `install()` (or use `callscope run`) before your app connects.

## A request shows 0 calls but I know it queries the database

The calls may be running in a thread that doesn't inherit the request's context. See [Threads](frameworks.md#threads). They are still printed live, just not counted in the request's summary.

## The N+1 warning fires on my setup code

At exit, callscope summarizes calls made outside any request, which includes startup code like seeding a database in a loop. That's often a real (if harmless) N+1. Raise the threshold with `--n-plus-one`, or wrap setup code in its own `callscope.scope("setup")`.

## Is it safe to use in production?

It's built for development, tests and CI. See [Privacy and security](privacy.md).

## How is this different from...

| Tool | Difference |
|---|---|
| Django Debug Toolbar, django-silk | Django only, no outgoing HTTP. callscope works with any framework and captures HTTP, SQL and Redis together. |
| httpdbg, Smello | HTTP only. callscope adds SQL and Redis, per-request grouping and N+1 detection. |
| Sentry, OpenTelemetry, Logfire | Production observability that needs an SDK setup, a collector or an account. callscope is one `pip install`, local only, aimed at the development loop. |

## Can I send calls to my own logger or a file?

Yes, with a [listener](api.md#callscopelistener).

## Which Python versions are supported?

Python 3.9 and newer, on Linux, macOS and Windows.
