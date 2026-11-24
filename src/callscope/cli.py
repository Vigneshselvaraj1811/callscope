"""``callscope run app.py`` / ``callscope run -m module``: capture calls with no code changes."""

from __future__ import annotations

import argparse
import os
import runpy
import sys

from . import __version__, install

USAGE = """\
usage: callscope run [options] script.py [args...]
       callscope run [options] -m module [args...]

See every HTTP, SQL and Redis call your Python program makes.

options:
  --quiet             only print summaries, not every call
  --only KINDS        comma-separated kinds or libraries, e.g. sql,http
  --slow-ms MS        slow call threshold in ms (default 500)
  --n-plus-one N      repeat count that flags an N+1 query (default 5)
  --version           show version and exit
  -h, --help          show this help and exit

examples:
  callscope run app.py
  callscope run -m uvicorn main:app
  callscope run --only sql -m pytest -x
"""

_VALUE_OPTIONS = {"--only", "--slow-ms", "--n-plus-one"}


def _split(argv: list) -> tuple:
    """Split ``run`` arguments into (callscope options, module, script, program args).

    Everything after the script or ``-m module`` belongs to the program, so
    ``callscope run -m pytest -x`` passes ``-x`` to pytest.
    """
    options: list = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "-m":
            if i + 1 >= len(argv):
                raise SystemExit("callscope: -m needs a module name")
            return options, argv[i + 1], None, argv[i + 2 :]
        if arg.startswith("-"):
            options.append(arg)
            if arg in _VALUE_OPTIONS:
                if i + 1 >= len(argv):
                    raise SystemExit(f"callscope: {arg} needs a value")
                options.append(argv[i + 1])
                i += 1
            i += 1
            continue
        return options, None, arg, argv[i + 1 :]
    return options, None, None, []


def _options_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="callscope run", add_help=False, usage=USAGE)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--only")
    parser.add_argument("--slow-ms", type=float, default=500)
    parser.add_argument("--n-plus-one", type=int, default=5)
    parser.add_argument("-h", "--help", action="store_true")
    return parser


def main(argv: list | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    if argv[0] == "--version":
        print(f"callscope {__version__}")
        return 0
    if argv[0] != "run":
        print(f"callscope: unknown command {argv[0]!r}\n\n{USAGE}", file=sys.stderr)
        return 2

    options, module, script, program_args = _split(argv[1:])
    ns = _options_parser().parse_args(options)
    if ns.help:
        print(USAGE)
        return 0
    if not module and not script:
        print(f"callscope: give a script path or -m module\n\n{USAGE}", file=sys.stderr)
        return 2
    if script and not os.path.exists(script):
        print(f"callscope: no such file: {script}", file=sys.stderr)
        return 2

    try:
        install(
            live=not ns.quiet,
            only=ns.only.split(",") if ns.only else None,
            slow_ms=ns.slow_ms,
            n_plus_one=ns.n_plus_one,
        )
    except ValueError as exc:
        print(f"callscope: {exc}", file=sys.stderr)
        return 2

    if module:
        sys.argv = [module, *program_args]
        sys.path.insert(0, os.getcwd())
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    else:
        path = os.path.abspath(script)
        sys.argv = [script, *program_args]
        sys.path.insert(0, os.path.dirname(path))
        runpy.run_path(path, run_name="__main__")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
