# Getting started

## 1. Install

```console
pip install callscope
```

callscope is a development tool. Add it to your dev dependencies, not production ones:

=== "uv"

    ```console
    uv add --dev callscope
    ```

=== "Poetry"

    ```console
    poetry add --group dev callscope
    ```

=== "pip"

    ```console
    pip install callscope
    ```

## 2. Run your program through callscope

Put `callscope run` in front of the command you already use:

```console
callscope run app.py
callscope run -m uvicorn main:app
callscope run -m flask --app app run
callscope run manage.py runserver --noreload
```

Every HTTP request, SQL query and Redis command now prints as it happens, with the line of your code that made it:

```console
  sql   SELECT * FROM users WHERE id = ?                              0.3ms  <- app.py:14 in get_user
  http  GET https://api.example.com/profile                           200  88.1ms  <- app.py:20 in get_user
```

When the program exits, callscope prints a summary of any calls made outside a request, with warnings.

## 3. Group calls per request

Add the middleware for your framework. Each request then ends with a one-line summary and any problems found:

```console
* GET /users -> 200  431ms total, 52 calls (1 http, 50 sql, 1 redis) taking 418ms
  ! n+1  49x same query: SELECT * FROM orders WHERE user_id = ?  <- views.py:15 in list_users
```

=== "FastAPI / Starlette"

    ```python
    from callscope.middleware import ASGIMiddleware

    app.add_middleware(ASGIMiddleware)
    ```

=== "Flask"

    ```python
    from callscope.middleware import WSGIMiddleware

    app.wsgi_app = WSGIMiddleware(app.wsgi_app)
    ```

=== "Django"

    ```python
    # settings.py
    MIDDLEWARE = [
        "callscope.middleware.DjangoMiddleware",  # first
        # ...
    ]
    ```

The middleware does nothing when callscope isn't installed, so it's harmless to leave in during development. See [Frameworks](frameworks.md) for details.

## 4. Or enable it from code

If you can't change the start command, call `install()` once at startup:

```python
import callscope

callscope.install()
```

!!! tip "Only in development"
    Guard it so it never runs in production:

    ```python
    import os

    if os.environ.get("CALLSCOPE"):
        import callscope

        callscope.install()
    ```

## Next steps

- [Catch N+1 queries in your tests](testing.md)
- [What each warning means](findings.md)
- [All command-line options](cli.md)
