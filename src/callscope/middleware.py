"""Group calls per incoming request.

FastAPI / Starlette / any ASGI app::

    app.add_middleware(callscope.middleware.ASGIMiddleware)

Flask / any WSGI app::

    app.wsgi_app = callscope.middleware.WSGIMiddleware(app.wsgi_app)

Django (add to ``MIDDLEWARE``, first entry)::

    "callscope.middleware.DjangoMiddleware"
"""

from __future__ import annotations

from ._events import scope


class ASGIMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, asgi_scope, receive, send):
        if asgi_scope.get("type") != "http":
            return await self.app(asgi_scope, receive, send)
        name = f"{asgi_scope.get('method', '')} {asgi_scope.get('path', '')}"
        with scope(name) as s:

            async def send_wrapper(message):
                if message.get("type") == "http.response.start":
                    s.status = message.get("status")
                await send(message)

            await self.app(asgi_scope, receive, send_wrapper)


class WSGIMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    def __call__(self, environ, start_response):
        name = f"{environ.get('REQUEST_METHOD', '')} {environ.get('PATH_INFO', '')}"
        with scope(name) as s:

            def start_response_wrapper(status, headers, exc_info=None):
                try:
                    s.status = int(str(status).split(" ", 1)[0])
                except ValueError:
                    pass
                return start_response(status, headers, exc_info)

            # Materialize the body inside the scope so calls made while streaming are counted.
            result = self.app(environ, start_response_wrapper)
            try:
                return list(result)
            finally:
                close = getattr(result, "close", None)
                if close is not None:
                    close()


class DjangoMiddleware:
    sync_capable = True
    async_capable = False

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        with scope(f"{request.method} {request.path}") as s:
            response = self.get_response(request)
            s.status = getattr(response, "status_code", None)
            return response
