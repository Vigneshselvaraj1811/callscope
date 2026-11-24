# Command line

```console
callscope run [options] script.py [args...]
callscope run [options] -m module [args...]
```

`callscope run` turns callscope on, then runs your script or module exactly as `python` would. `sys.argv`, `__name__ == "__main__"` and exit codes behave the same.

Everything after the script name, or after `-m module`, is passed to your program. callscope's own options go **before** it:

```console
callscope run --quiet -m pytest -x      # --quiet is for callscope, -x is for pytest
```

## Options

| Option | Default | Description |
|---|---|---|
| `--quiet` | off | Print only per-request summaries and warnings, not every call. |
| `--only KINDS` | all | Comma-separated kinds or libraries to capture: `http`, `sql`, `redis`, or `requests`, `httpx`, `sqlite3`, `sqlalchemy`, `django`. |
| `--slow-ms MS` | `500` | Flag calls that take this long or longer. |
| `--n-plus-one N` | `5` | Flag a query shape repeated this many times in one request. |
| `--version` | | Print the version and exit. |
| `-h`, `--help` | | Print help and exit. |

## Examples

```console
# A script
callscope run app.py

# A web server
callscope run -m uvicorn main:app --port 8000
callscope run -m flask --app app run
callscope run manage.py runserver --noreload

# Only SQL, only summaries
callscope run --quiet --only sql -m uvicorn main:app

# Stricter thresholds while optimizing an endpoint
callscope run --slow-ms 100 --n-plus-one 3 app.py

# Your test suite
callscope run --quiet -m pytest
```

## Output

callscope writes to **stderr**, so your program's stdout stays clean and can still be piped.

Colors are used when stderr is a terminal. Set `NO_COLOR=1` to turn them off, or `FORCE_COLOR=1` to force them on (for example in CI logs).

`python -m callscope run ...` works the same as `callscope run ...`.
