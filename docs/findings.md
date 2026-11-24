# Findings explained

At the end of each request (and at program exit for calls outside a request), callscope checks the calls for three problems. Each finding names the line of your code most responsible.

## N+1 queries

```console
  ! n+1  49x same query: SELECT * FROM orders WHERE user_id = ?  <- views.py:15 in list_users
```

**What it means:** the same query *shape* ran many times in one request. This almost always comes from a loop that runs one query per item:

```python
users = User.objects.all()
for user in users:
    print(user.orders.count())  # one query per user
```

**How it's detected:** callscope normalizes each SQL statement, replacing literals and placeholders with `?` and collapsing `IN (...)` lists, then counts how many times each shape appears. `WHERE id = 1` and `WHERE id = 2` are the same shape. The default threshold is **5 repeats** (`--n-plus-one` / `n_plus_one=`).

**How to fix it:** load related data in one query.

| Library | Fix |
|---|---|
| Django | `select_related()` for foreign keys, `prefetch_related()` for many-to-many and reverse relations, or `annotate(Count(...))` |
| SQLAlchemy | `selectinload()` / `joinedload()` options, or a `JOIN` with `GROUP BY` |
| Raw SQL | One query with `WHERE id IN (...)` or a `JOIN` |

## Duplicate calls

```console
  ! duplicate  2x identical http call: GET https://api.example.com/rates  <- billing.py:30 in sync
```

**What it means:** the exact same HTTP request, or the same Redis command on the same key, ran more than once in one request. Pipelines are not checked.

**How to fix it:** call once and reuse the result, for example by passing it down or caching it for the duration of the request.

## Slow calls

```console
  ! slow  2025ms http: GET https://api.example.com/report  <- reports.py:12 in build
```

**What it means:** a single call took at least the slow threshold, **500 ms** by default (`--slow-ms` / `slow_ms=`).

**How to fix it:** for SQL, run `EXPLAIN` and check for missing indexes. For HTTP, add a timeout, cache the result, or move the call to a background job.

## Tuning

```console
callscope run --n-plus-one 3 --slow-ms 100 app.py
```

```python
callscope.install(n_plus_one=3, slow_ms=100)
```

Set either to `0` to turn that check off.
