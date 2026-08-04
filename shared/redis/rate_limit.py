from __future__ import annotations

import logging

from shared.redis.client import get_redis, is_redis_enabled

logger = logging.getLogger(__name__)


async def is_rate_limited(key: str, *, max_attempts: int, window_seconds: int) -> bool:
    """Return True when the key has exceeded allowed attempts in the window."""
    if not is_redis_enabled():
        return False

    redis = get_redis()
    if redis is None:
        return False

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window_seconds)

    if count > max_attempts:
        logger.warning("Rate limit exceeded for key=%s count=%s", key, count)
        return True

    return False
