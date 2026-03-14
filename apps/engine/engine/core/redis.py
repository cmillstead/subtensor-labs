"""Async Redis connection and cache helpers."""

import threading
from typing import cast

from redis.asyncio import Redis

from engine.core.config import settings
from engine.core.logging import get_logger

log = get_logger(__name__)

_redis_client: Redis | None = None
_redis_lock = threading.Lock()


def get_redis() -> Redis:
    """Get or create the Redis client (thread-safe)."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                _redis_client = Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    max_connections=settings.redis_max_connections,
                )
    return _redis_client


async def check_redis_health() -> bool:
    """Check if Redis is reachable."""
    try:
        result = await get_redis().ping()  # type: ignore[misc]  # redis-py async stubs return Awaitable[ResponseT]
        return bool(result)
    except Exception:
        log.warning("redis_health_check_failed", exc_info=True)
        return False


async def cache_get(key: str) -> str | None:
    """Get a value from Redis cache."""
    result = await get_redis().get(key)
    return cast("str | None", result)


async def cache_set(key: str, value: str, ttl: int) -> None:
    """Set a value in Redis cache with TTL in seconds."""
    await get_redis().set(key, value, ex=ttl)


async def cache_delete(key: str) -> None:
    """Delete a key from Redis cache."""
    await get_redis().delete(key)


async def close_redis() -> None:
    """Close the Redis connection on shutdown."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
