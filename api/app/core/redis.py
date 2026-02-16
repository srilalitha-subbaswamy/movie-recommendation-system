"""Redis client with circuit breaker pattern for cache failures."""

import json
from typing import Any

import redis.asyncio as redis
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

settings = get_settings()

redis_client: redis.Redis | None = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        await redis_client.ping()
        logger.info("redis_connected", url=settings.REDIS_URL)
    except Exception:
        logger.warning("redis_connection_failed", url=settings.REDIS_URL)
        redis_client = None


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def cache_get(key: str) -> Any | None:
    """Get a value from cache, returning None on any failure."""
    if redis_client is None:
        return None
    try:
        value = await redis_client.get(key)
        if value is not None:
            return json.loads(value)
    except Exception:
        logger.warning("cache_get_failed", key=key)
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Set a value in cache, silently failing on errors."""
    if redis_client is None:
        return
    try:
        await redis_client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        logger.warning("cache_set_failed", key=key)


async def cache_delete(key: str) -> None:
    """Delete a key from cache."""
    if redis_client is None:
        return
    try:
        await redis_client.delete(key)
    except Exception:
        logger.warning("cache_delete_failed", key=key)


def get_redis() -> redis.Redis | None:
    """Get the Redis client instance."""
    return redis_client
