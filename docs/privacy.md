# Privacy and security

callscope is built to be safe to run on real data during development.

## Nothing leaves your machine

callscope makes no network requests of its own, has no telemetry and needs no account. Calls are printed to your terminal and passed to listeners you register. Nothing else.

## What is masked or never printed

| Data | Handling |
|---|---|
| Passwords in URLs (`https://user:pass@host`) | Password replaced with `***` |
| Query parameters whose names contain `password`, `secret`, `token`, `key`, `auth`, `signature`, `sig`, `session`, `credential` or `code` | Value replaced with `***` |
| SQL parameters (the values bound to `?` / `%s`) | Never captured |
| Redis values | Never captured. Only the command name and first key are shown. |
| HTTP request and response bodies and headers | Never captured |

!!! warning "Literals written into SQL"
    If your code puts values directly into the SQL string instead of using parameters, those values are part of the statement and will be printed. (That's also a SQL injection risk worth fixing.)

## Use in development only

callscope patches libraries in your process. It's designed for local development, tests and CI, not production servers. Keep it in your dev dependencies, or enable it only behind an environment variable.

## Reporting a vulnerability

See [SECURITY.md](https://github.com/Vigneshselvaraj1811/callscope/blob/main/SECURITY.md). Please report security issues privately, not in public issues.
