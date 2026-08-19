from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_redis: Redis | None = None


def is_redis_enabled() -> bool:
    from gateway.config import settings

    return settings.REDIS_ENABLED


def _redis_url() -> str:
    from gateway.config import settings

    return settings.REDIS_URL


async def init_redis() -> None:
    global _redis

    if not is_redis_enabled():
        logger.info("Redis disabled — using in-process fallbacks where applicable")
        return

    from redis.asyncio import Redis

    try:
        _redis = Redis.from_url(_redis_url(), decode_responses=True)
        await _redis.ping()
        logger.info("Redis connected at %s", _redis_url())
    except Exception:
        logger.warning(
            "Redis unavailable at %s — events will log locally; rate limits skipped",
            _redis_url(),
        )
        _redis = None


async def close_redis() -> None:
    global _redis

    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


def get_redis() -> Redis | None:
    return _redis


async def ping_redis() -> bool:
    if _redis is None:
        return False
    try:
        await _redis.ping()
        return True
    except Exception:
        logger.exception("Redis ping failed")
        return False
