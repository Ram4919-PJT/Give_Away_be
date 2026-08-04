from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from shared.redis.client import get_redis, is_redis_enabled
from shared.redis.keys import EVENTS_STREAM

logger = logging.getLogger(__name__)


async def publish_event(event_type: str, payload: dict[str, Any]) -> str | None:
    """Publish an event to the Redis stream. Returns event id or None if Redis is off."""
    event_id = str(uuid.uuid4())
    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "payload": json.dumps(payload),
    }

    if not is_redis_enabled():
        logger.info("Event (no Redis): %s payload=%s", event_type, payload)
        return event_id

    redis = get_redis()
    if redis is None:
        logger.info("Event (Redis unavailable): %s payload=%s", event_type, payload)
        return event_id

    await redis.xadd(EVENTS_STREAM, envelope)
    logger.info("Event published: %s id=%s", event_type, event_id)
    return event_id


async def ensure_consumer_group(group_name: str) -> None:
    redis = get_redis()
    if redis is None:
        return

    try:
        await redis.xgroup_create(EVENTS_STREAM, group_name, id="0", mkstream=True)
        logger.info("Created Redis consumer group %s", group_name)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def read_group_events(
    *,
    group_name: str,
    consumer_name: str,
    count: int = 10,
    block_ms: int = 5000,
) -> list[tuple[str, dict[str, str]]]:
    """Read pending events for a consumer group. Returns [(message_id, fields), ...]."""
    redis = get_redis()
    if redis is None:
        return []

    raw = await redis.xreadgroup(
        groupname=group_name,
        consumername=consumer_name,
        streams={EVENTS_STREAM: ">"},
        count=count,
        block=block_ms,
    )

    messages: list[tuple[str, dict[str, str]]] = []
    for _stream, entries in raw:
        for message_id, fields in entries:
            messages.append((message_id, fields))
    return messages


async def ack_event(group_name: str, message_id: str) -> None:
    redis = get_redis()
    if redis is None:
        return
    await redis.xack(EVENTS_STREAM, group_name, message_id)


async def is_event_processed(consumer: str, event_id: str) -> bool:
    redis = get_redis()
    if redis is None:
        return False

    from shared.redis.keys import EVENT_PROCESSED

    key = EVENT_PROCESSED.format(consumer=consumer, event_id=event_id)
    return await redis.exists(key) == 1


async def mark_event_processed(consumer: str, event_id: str, ttl_seconds: int = 86400) -> None:
    redis = get_redis()
    if redis is None:
        return

    from shared.redis.keys import EVENT_PROCESSED

    key = EVENT_PROCESSED.format(consumer=consumer, event_id=event_id)
    await redis.set(key, "1", ex=ttl_seconds)
