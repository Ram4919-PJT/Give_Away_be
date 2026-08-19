from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from core_app.db.session import AsyncSessionLocal
from core_app.services import core_service
from shared.redis.events import (
    ack_event,
    ensure_consumer_group,
    is_event_processed,
    mark_event_processed,
    read_group_events,
)

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "core-service"
CONSUMER_NAME = "core-worker-1"


async def _handle_user_registered(payload: dict) -> None:
    async with AsyncSessionLocal() as db:
        await core_service.create_profile_from_registration(
            db,
            user_id=UUID(payload["user_id"]),
            role=payload["role"],
            full_name=payload.get("full_name", ""),
            email=payload.get("email", ""),
        )
    logger.info("Created profile stub for user_id=%s role=%s", payload.get("user_id"), payload.get("role"))


HANDLERS = {
    "user.registered": _handle_user_registered,
}


async def _process_message(message_id: str, fields: dict[str, str]) -> None:
    event_id = fields.get("event_id", message_id)
    event_type = fields.get("event_type", "")
    payload_raw = fields.get("payload", "{}")

    if await is_event_processed(CONSUMER_GROUP, event_id):
        await ack_event(CONSUMER_GROUP, message_id)
        return

    handler = HANDLERS.get(event_type)
    if handler:
        payload = json.loads(payload_raw)
        await handler(payload)
        await mark_event_processed(CONSUMER_GROUP, event_id)
    else:
        logger.debug("Core consumer ignoring event_type=%s", event_type)

    await ack_event(CONSUMER_GROUP, message_id)


async def run_core_consumer() -> None:
    await ensure_consumer_group(CONSUMER_GROUP)
    logger.info("Core event consumer started (group=%s)", CONSUMER_GROUP)

    while True:
        try:
            messages = await read_group_events(
                group_name=CONSUMER_GROUP,
                consumer_name=CONSUMER_NAME,
            )
            if not messages:
                continue

            for message_id, fields in messages:
                try:
                    await _process_message(message_id, fields)
                except Exception:
                    logger.exception("Failed to process core event message_id=%s", message_id)
        except asyncio.CancelledError:
            logger.info("Core event consumer stopped")
            raise
        except Exception:
            logger.exception("Core consumer loop error")
            await asyncio.sleep(2)
