# Releasing callscope

Releases are published by GitHub Actions using **PyPI Trusted Publishing**.
No API token is created, stored or shared.

## One-time setup

1. Push this repository to GitHub.
2. On PyPI, go to **Your account → Publishing → Add a new pending publisher** and fill in:
   - PyPI project name: `callscope`
   - Owner: your GitHub user or organization
   - Repository name: `callscope`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`
3. In the GitHub repository, go to **Settings → Environments → New environment** and create `pypi`.
   Optionally add yourself as a required reviewer so every release waits for your approval.
4. In the GitHub repository, go to **Settings → Pages** and set **Source** to **GitHub Actions** so the docs site publishes.

## Each release

1. Update `__version__` in `src/callscope/__init__.py` and the date in `CHANGELOG.md`.
2. Commit, then tag: `git tag v0.1.0 && git push --tags`.
3. On GitHub, create a Release from the tag. The Publish workflow builds, checks and uploads it.

## Trying it on TestPyPI first (optional)

```console
uv build
uvx twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ callscope
```

This one needs a TestPyPI token in your local `~/.pypirc` (`chmod 600`). Never paste tokens into chats or commit them.
