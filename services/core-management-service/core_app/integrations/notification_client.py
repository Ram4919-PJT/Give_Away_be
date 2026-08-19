from __future__ import annotations

import logging
from typing import Any

import httpx

from core_app.config import settings

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    return {"X-Internal-Key": settings.INTERNAL_NOTIFICATION_KEY}


async def notify_user(
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "DONATION",
    event_type: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    action_url: str | None = None,
    recipient_email: str | None = None,
    recipient_name: str | None = None,
    template_data: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    send_in_app: bool = True,
    send_email: bool = True,
) -> None:
    if not settings.NOTIFICATIONS_ENABLED:
        return
    payload = {
        "user_id": user_id,
        "title": title,
        "message": message,
        "notification_type": notification_type,
        "event_type": event_type,
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
        "action_url": action_url,
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "template_data": template_data,
        "idempotency_key": idempotency_key,
        "send_in_app": send_in_app,
        "send_email": send_email,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{settings.GATEWAY_INTERNAL_URL.rstrip('/')}/api/v1/notifications/internal",
                json=payload,
                headers=_headers(),
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to send notification to user %s: %s", user_id, exc)


async def dispatch_email_only(
    *,
    user_id: int | None = None,
    recipient_email: str | None = None,
    recipient_name: str | None = None,
    event_type: str,
    title: str,
    message: str,
    notification_type: str = "ACCOUNT",
    template_data: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    action_url: str | None = None,
) -> None:
    if not settings.NOTIFICATIONS_ENABLED:
        return
    payload = {
        "user_id": user_id,
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "event_type": event_type,
        "notification_type": notification_type,
        "title": title,
        "message": message,
        "template_data": template_data,
        "idempotency_key": idempotency_key,
        "action_url": action_url,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{settings.GATEWAY_INTERNAL_URL.rstrip('/')}/api/v1/notifications/internal/email",
                json=payload,
                headers=_headers(),
            )
            response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to dispatch email (%s): %s", event_type, exc)
