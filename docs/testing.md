# Catching N+1 in tests

The best time to catch an N+1 query is before it ships. callscope's [`scope()`](api.md#callscopescope) counts the calls made inside a block, so a test can assert a limit.

## A query budget per endpoint

=== "FastAPI"

    ```python
    import callscope
    from fastapi.testclient import TestClient

    from myapp import app


    def test_list_users_query_budget():
        callscope.install(report=False)
        client = TestClient(app)
        with callscope.scope("GET /users") as s:
            assert client.get("/users").status_code == 200
        assert s.count("sql") <= 3, s.counts()
    ```

=== "Django"

    ```python
    import callscope


    def test_list_users_query_budget(client):
        callscope.install(report=False)
        with callscope.scope("GET /users") as s:
            assert client.get("/users/").status_code == 200
        assert s.count("sql") <= 3, s.counts()
    ```

=== "Flask"

    ```python
    import callscope

    from myapp import app


    def test_list_users_query_budget():
        callscope.install(report=False)
        with callscope.scope("GET /users") as s:
            assert app.test_client().get("/users").status_code == 200
        assert s.count("sql") <= 3, s.counts()
    ```

`report=False` keeps the terminal output out of your test logs.

## Fail on any N+1, whatever the count

Use [`analyze()`](api.md#callscopeanalyze) to check for the pattern instead of a fixed number:

```python
import callscope


def test_no_n_plus_one(client):
    callscope.install(report=False)
    with callscope.scope("GET /orders") as s:
        client.get("/orders")
    problems = [f for f in callscope.analyze(s.calls, n_plus_one=3) if f.kind == "n+1"]
    assert not problems, "\n".join(f"{f.message} at {f.location}" for f in problems)
```

The failure message says which query repeated and which line made it.

## A reusable fixture

```python
# conftest.py
import pytest
import callscope


@pytest.fixture
def calls():
    callscope.install(report=False)
    with callscope.scope("test") as s:
        yield s
    callscope.uninstall()
```

```python
def test_profile_page(client, calls):
    client.get("/profile")
    assert calls.count("sql") <= 2
    assert calls.count("http") == 0  # nothing should call out to the network
```

!!! note "Middleware in tests"
    If your app also has callscope's middleware, the request gets its own nested scope and the calls are recorded there, not in the test's scope. Either leave the middleware out of your test settings, or read the request's scope with a [listener](api.md#callscopelistener).
