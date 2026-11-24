# Contributing to callscope

Thanks for helping! Bug reports, docs fixes, new instruments and ideas are all welcome.

## Ways to help

- **Report a bug:** open an [issue](https://github.com/Vigneshselvaraj1811/callscope/issues/new/choose) with the smallest code that shows the problem.
- **Suggest a feature or a library to support:** open a feature request and describe what you'd use it for.
- **Improve the docs:** every docs page has an edit button. Small fixes can go straight to a pull request.
- **Write code:** look for issues labeled `good first issue` or `help wanted`. For anything big, open an issue first so we can agree on the approach.

## Development setup

You need Python 3.9+ and [uv](https://docs.astral.sh/uv/) (or plain `pip`).

```console
git clone https://github.com/Vigneshselvaraj1811/callscope
cd callscope
uv venv
uv pip install -e ".[test,docs]"
```

## Before you open a pull request

```console
python -m pytest            # all tests must pass
uvx ruff check .            # lint
uvx ruff format .           # format
mkdocs serve                # if you changed docs, preview at http://127.0.0.1:8000
```

CI runs the same checks on Python 3.9 to 3.14 on Linux, plus macOS and Windows, and once with no optional libraries installed.

## Guidelines

- **No new runtime dependencies.** callscope must stay a zero-dependency install. Libraries go in the `test` extra only.
- **Never break the user's app.** Instruments must re-raise the original exception unchanged, and listener errors are swallowed. If something goes wrong inside callscope, the user's call must still behave exactly as without it.
- **Never print secrets.** No request bodies, headers, SQL parameters or Redis values. Mask anything sensitive in URLs.
- **Every instrument needs `install()` and `uninstall()`**, must be idempotent, and must return `False` when its library isn't installed.
- **Add tests** for every bug fix and feature. Use local servers and in-memory databases, never the real network.
- **Keep the public API small.** New public names go in `callscope/__init__.py`'s `__all__` and in `docs/api.md`.
- **Update `CHANGELOG.md`** under "Unreleased".

## Adding an instrument

1. Create `src/callscope/instruments/_yourlib.py` with `install() -> bool` and `uninstall() -> None`. Use `timed()` / `atimed()` from `callscope._events` to wrap a call, or `begin()` / `finish()` for event-based hooks.
2. Register it in `INSTRUMENTS` and `KINDS` in `src/callscope/instruments/__init__.py`.
3. Add tests in `tests/`, using `pytest.importorskip("yourlib")`.
4. Add it to the tables in `README.md`, `docs/index.md` and `docs/how-it-works.md`.

## Code of conduct

This project follows the [Code of Conduct](https://github.com/Vigneshselvaraj1811/callscope/blob/main/CODE_OF_CONDUCT.md). By taking part, you agree to follow it.
