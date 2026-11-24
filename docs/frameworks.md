# Frameworks

callscope captures calls from any Python program. The middleware adds one thing: it **groups the calls made during each incoming request**, so you get a summary and warnings per request instead of one long stream.

Every middleware records the request's method, path, status code and total duration.

## FastAPI and Starlette

```python
from fastapi import FastAPI
from callscope.middleware import ASGIMiddleware

app = FastAPI()
app.add_middleware(ASGIMiddleware)
```

Run it:

```console
callscope run -m uvicorn main:app
```

Both `async def` and plain `def` endpoints are grouped correctly. FastAPI runs plain `def` endpoints in a worker thread with a copy of the request's context, and callscope follows that context.

`ASGIMiddleware` works with any ASGI application: Starlette, Litestar, Quart, Django's ASGI handler and others. Only `http` requests are grouped. WebSocket and lifespan events pass straight through.

!!! warning "`--reload`"
    `uvicorn --reload` runs your app in a child process that `callscope run` doesn't reach. Either drop `--reload` while profiling, or call `callscope.install()` in your app module.

## Flask

```python
from flask import Flask
from callscope.middleware import WSGIMiddleware

app = Flask(__name__)
app.wsgi_app = WSGIMiddleware(app.wsgi_app)
```

Run it:

```console
callscope run -m flask --app app run
```

`WSGIMiddleware` works with any WSGI application: Flask, Bottle, Pyramid, Falcon and others.

!!! note "Streaming responses"
    `WSGIMiddleware` reads the whole response body inside the request, so calls made while a response streams are counted. Don't use it on endpoints that stream very large downloads.

## Django

Add the middleware **first** in `MIDDLEWARE`, so it sees the queries made by every other middleware too:

```python
# settings.py
MIDDLEWARE = [
    "callscope.middleware.DjangoMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # ...
]
```

Run it:

```console
callscope run manage.py runserver --noreload
```

Django ORM queries are captured through Django's official [`execute_wrappers`](https://docs.djangoproject.com/en/stable/topics/db/instrumentation/) hook, so this works with every database backend Django supports. Each query is counted once, even on SQLite.

!!! warning "Autoreloader"
    Without `--noreload`, Django serves requests from a child process. Either use `--noreload`, or call `callscope.install()` in `settings.py` or `manage.py`.

`DjangoMiddleware` is sync-only. For async Django under an ASGI server, use `ASGIMiddleware` around the ASGI application instead:

```python
# asgi.py
from django.core.asgi import get_asgi_application
from callscope.middleware import ASGIMiddleware

application = ASGIMiddleware(get_asgi_application())
```

## Scripts, workers and anything else

No middleware needed. Run the program with `callscope run` and you get a live stream plus a summary at exit.

To get per-job summaries in a worker, wrap each unit of work in a scope:

```python
import callscope


def handle(job):
    with callscope.scope(f"job {job.id}"):
        process(job)
```

## Threads

Calls are grouped through Python's `contextvars`. A thread you start yourself doesn't inherit the request's context, so its calls appear without a request. To keep them grouped, run the thread inside a copy of the context:

```python
import contextvars
import threading

ctx = contextvars.copy_context()
threading.Thread(target=ctx.run, args=(work,)).start()
```

`asyncio` tasks, `asyncio.to_thread`, and FastAPI and Starlette's thread pools already do this.
