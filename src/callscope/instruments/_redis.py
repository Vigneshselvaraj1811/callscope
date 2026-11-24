"""redis-py (sync and asyncio). Only the command name and first key are shown,
never values, so cached secrets and session data stay out of your terminal."""

from __future__ import annotations

from .._events import atimed, timed

_originals: dict = {}


def _fmt(args) -> str:
    if not args:
        return "?"
    command = str(args[0]).upper()
    if len(args) > 1:
        key = args[1]
        if isinstance(key, bytes):
            key = key.decode("utf-8", "replace")
        key = str(key)
        if len(key) > 80:
            key = key[:77] + "..."
        return f"{command} {key}"
    return command


def _pipeline_target(pipe) -> str:
    stack = getattr(pipe, "command_stack", None) or []
    names = []
    for entry in stack[:5]:
        args = entry[0] if isinstance(entry, tuple) else getattr(entry, "args", ())
        names.append(str(args[0]).upper() if args else "?")
    more = f", +{len(stack) - 5}" if len(stack) > 5 else ""
    return f"PIPELINE[{len(stack)}] {', '.join(names)}{more}"


def install() -> bool:
    try:
        from redis.client import Pipeline, Redis
    except ImportError:
        return False
    if _originals:
        return True

    execute_command = _originals["Redis.execute_command"] = Redis.execute_command
    pipeline_execute = _originals["Pipeline.execute"] = Pipeline.execute

    def patched_execute_command(self, *args, **options):
        return timed("redis", _fmt(args), None, execute_command, self, *args, **options)

    def patched_pipeline_execute(self, *args, **kwargs):
        return timed("redis", _pipeline_target(self), None, pipeline_execute, self, *args, **kwargs)

    Redis.execute_command = patched_execute_command
    Pipeline.execute = patched_pipeline_execute

    try:
        from redis.asyncio.client import Pipeline as AsyncPipeline
        from redis.asyncio.client import Redis as AsyncRedis
    except ImportError:
        return True

    async_execute = _originals["AsyncRedis.execute_command"] = AsyncRedis.execute_command
    async_pipeline = _originals["AsyncPipeline.execute"] = AsyncPipeline.execute

    async def patched_async_execute(self, *args, **options):
        return await atimed("redis", _fmt(args), None, async_execute, self, *args, **options)

    async def patched_async_pipeline(self, *args, **kwargs):
        return await atimed(
            "redis", _pipeline_target(self), None, async_pipeline, self, *args, **kwargs
        )

    AsyncRedis.execute_command = patched_async_execute
    AsyncPipeline.execute = patched_async_pipeline
    return True


def uninstall() -> None:
    if not _originals:
        return
    from redis.client import Pipeline, Redis

    Redis.execute_command = _originals.pop("Redis.execute_command")
    Pipeline.execute = _originals.pop("Pipeline.execute")
    if "AsyncRedis.execute_command" in _originals:
        from redis.asyncio.client import Pipeline as AsyncPipeline
        from redis.asyncio.client import Redis as AsyncRedis

        AsyncRedis.execute_command = _originals.pop("AsyncRedis.execute_command")
        AsyncPipeline.execute = _originals.pop("AsyncPipeline.execute")
