"""Real framework apps, exercised through each framework's own test client."""

import sqlite3

import pytest

import callscope


class _Collect(callscope.Listener):
    def __init__(self):
        self.scopes = []

    def on_scope_end(self, scope):
        self.scopes.append(scope)


@pytest.fixture
def collected():
    listener = _Collect()
    callscope.add_listener(listener)
    yield listener.scopes
    callscope.remove_listener(listener)


def _n_plus_one(conn, n=6):
    conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
    for i in range(n):
        conn.execute("SELECT * FROM t WHERE id = ?", (i,))


def test_fastapi_sync_and_async_endpoints(collected):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from callscope.middleware import ASGIMiddleware

    app = FastAPI()
    app.add_middleware(ASGIMiddleware)

    @app.get("/sync")
    def sync_endpoint():  # runs in a worker thread
        _n_plus_one(sqlite3.connect(":memory:"))
        return {"ok": True}

    @app.get("/async")
    async def async_endpoint():
        _n_plus_one(sqlite3.connect(":memory:"))
        return {"ok": True}

    with TestClient(app) as client:
        assert client.get("/sync").status_code == 200
        assert client.get("/async").status_code == 200
        assert client.get("/nope").status_code == 404

    by_name = {s.name: s for s in collected}
    for name in ("GET /sync", "GET /async"):
        # TestClient's own httpx request must not hide the app's queries.
        assert by_name[name].count("sql") == 7, name
        assert by_name[name].status == 200
        assert [f.kind for f in callscope.analyze(by_name[name].calls)] == ["n+1"]
    assert by_name["GET /nope"].status == 404


def test_flask(collected):
    pytest.importorskip("flask")
    from flask import Flask

    from callscope.middleware import WSGIMiddleware

    app = Flask(__name__)
    app.wsgi_app = WSGIMiddleware(app.wsgi_app)

    @app.get("/posts")
    def posts():
        _n_plus_one(sqlite3.connect(":memory:"))
        return {"ok": True}

    client = app.test_client()
    assert client.get("/posts").status_code == 200
    assert client.get("/nope").status_code == 404

    assert [(s.name, s.status, s.count("sql")) for s in collected] == [
        ("GET /posts", 200, 7),
        ("GET /nope", 404, 0),
    ]


def test_django_orm_and_middleware(collected, tmp_path):
    pytest.importorskip("django")
    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            SECRET_KEY="test",
            ROOT_URLCONF=__name__,
            ALLOWED_HOSTS=["*"],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": str(tmp_path / "db.sqlite3"),
                }
            },
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
            MIDDLEWARE=["callscope.middleware.DjangoMiddleware"],
        )
        django.setup()
    from django.contrib.auth.models import User
    from django.core.management import call_command
    from django.test import Client

    call_command("migrate", verbosity=0)
    User.objects.bulk_create([User(username=f"u{i}") for i in range(6)])

    global urlpatterns
    from django.http import JsonResponse
    from django.urls import clear_url_caches, path

    def users(request):
        data = [u.groups.count() for u in User.objects.all()]  # N+1
        return JsonResponse({"n": len(data)})

    urlpatterns = [path("users/", users)]
    clear_url_caches()

    assert Client().get("/users/").status_code == 200

    scope = next(s for s in collected if s.name == "GET /users/")
    assert scope.status == 200
    # 1 query for users + 6 group counts, each recorded once (no sqlite3 double count).
    assert scope.count("sql") == 7
    assert all(c.detail["db"] == "sqlite" for c in scope.calls)
    assert all("test_frameworks.py" in c.location for c in scope.calls)
    assert [f.kind for f in callscope.analyze(scope.calls)] == ["n+1"]


urlpatterns: list = []
