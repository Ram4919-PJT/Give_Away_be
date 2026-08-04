from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from comm_app.db.session import AsyncSessionLocal
from comm_app.services import notification_service
from shared.redis.events import (
    ack_event,
    ensure_consumer_group,
    is_event_processed,
    mark_event_processed,
    read_group_events,
)

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "communication-service"
CONSUMER_NAME = "comm-worker-1"


async def _handle_user_registered(payload: dict) -> None:
    user_id = UUID(payload["user_id"])
    role = payload.get("role", "USER").replace("_", " ").title()
    async with AsyncSessionLocal() as db:
        await notification_service.create_system_notification(
            db,
            user_id=user_id,
            title="Welcome to Give Away",
            body=f"Your {role} account is ready. Complete your profile to get started.",
        )
    logger.info("Welcome notification created for user_id=%s", payload.get("user_id"))


async def _handle_otp_sent(payload: dict) -> None:
    user_id = UUID(payload["user_id"])
    purpose = payload.get("purpose", "verification").replace("_", " ").lower()
    async with AsyncSessionLocal() as db:
        await notification_service.create_system_notification(
            db,
            user_id=user_id,
            title="OTP sent",
            body=f"A one-time password for {purpose} was sent. Check your registered contact.",
        )


HANDLERS = {
    "user.registered": _handle_user_registered,
    "otp.sent": _handle_otp_sent,
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
        logger.debug("Communication consumer ignoring event_type=%s", event_type)

    await ack_event(CONSUMER_GROUP, message_id)


async def run_communication_consumer() -> None:
    await ensure_consumer_group(CONSUMER_GROUP)
    logger.info("Communication event consumer started (group=%s)", CONSUMER_GROUP)

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
                    logger.exception(
                        "Failed to process communication event message_id=%s", message_id
                    )
        except asyncio.CancelledError:
            logger.info("Communication event consumer stopped")
            raise
        except Exception:
            logger.exception("Communication consumer loop error")
            await asyncio.sleep(2)
