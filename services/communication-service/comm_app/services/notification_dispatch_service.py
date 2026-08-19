"""Central notification dispatch — in-app + email."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comm_app.config import settings
from comm_app.integrations.iam_client import resolve_user_contact
from comm_app.models.email_delivery import EmailDeliveryLog
from comm_app.models.notification import Notification, NotificationDeliveryLog, UserNotificationPreference
from comm_app.models.notification_events import EVENT_EMAIL_CONFIG, NOTIFICATION_TYPE_TO_CATEGORY
from comm_app.schemas.notification import InternalNotificationCreate
from comm_app.services.email_service import send_email, validate_recipient
from comm_app.services.email_template_service import render_email_template

logger = logging.getLogger(__name__)

UNREAD_STATUS = "UNREAD"
VALID_TYPES = {"DONATION", "CAMPAIGN", "ACCOUNT", "SYSTEM", "APPLICATION"}


def _absolute_url(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = settings.APP_PUBLIC_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


async def _email_enabled_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    preference_category: str,
    force_send: bool,
) -> bool:
    if force_send:
        return True
    result = await db.execute(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id,
            UserNotificationPreference.channel == "EMAIL",
        )
    )
    pref = result.scalar_one_or_none()
    if pref is None:
        return True
    return bool(pref.enabled)


async def _existing_idempotency(db: AsyncSession, key: str | None) -> EmailDeliveryLog | None:
    if not key:
        return None
    result = await db.execute(
        select(EmailDeliveryLog).where(EmailDeliveryLog.idempotency_key == key)
    )
    return result.scalar_one_or_none()


async def dispatch_email(
    db: AsyncSession,
    *,
    user_id: int | None,
    recipient_email: str | None,
    recipient_name: str | None,
    event_type: str,
    notification_type: str,
    title: str,
    message: str,
    template_data: dict[str, Any] | None,
    related_entity_type: str | None,
    related_entity_id: int | None,
    action_url: str | None,
    idempotency_key: str | None,
) -> EmailDeliveryLog:
    existing = await _existing_idempotency(db, idempotency_key)
    if existing and existing.status in {"SENT", "SKIPPED"}:
        return existing

    event_key = (event_type or "GENERIC_NOTIFICATION").upper()
    event_cfg = EVENT_EMAIL_CONFIG.get(event_key) or EVENT_EMAIL_CONFIG["GENERIC_NOTIFICATION"]

    contact = None
    if recipient_email:
        contact = {"email": recipient_email, "name": recipient_name or "there"}
    elif user_id:
        contact = await resolve_user_contact(user_id)

    email = validate_recipient(contact.get("email") if contact else None)
    display_name = (recipient_name or (contact or {}).get("name") or "there").strip()

    log = existing or EmailDeliveryLog(
        user_id=user_id,
        recipient_email=email or (recipient_email or ""),
        notification_type=notification_type,
        event_type=event_key,
        subject=event_cfg.subject,
        status="PENDING",
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        idempotency_key=idempotency_key,
    )
    if not existing:
        db.add(log)
        await db.flush()

    if not email:
        log.status = "SKIPPED"
        log.error_message = "No valid recipient email"
        await db.commit()
        await db.refresh(log)
        return log

    log.recipient_email = email

    if user_id and not await _email_enabled_for_user(
        db,
        user_id,
        preference_category=event_cfg.preference_category,
        force_send=event_cfg.force_send,
    ):
        log.status = "SKIPPED"
        log.error_message = "Email notifications disabled by user preference"
        await db.commit()
        await db.refresh(log)
        return log

    if not settings.EMAIL_ENABLED:
        log.status = "SKIPPED"
        log.error_message = "EMAIL_ENABLED=false"
        await db.commit()
        await db.refresh(log)
        return log

    ctx: dict[str, Any] = {
        "user_name": display_name,
        "recipient_name": display_name,
        "title": title,
        "message": message,
        "action_url": _absolute_url(action_url),
        **(template_data or {}),
    }
    _, html_body = render_email_template(event_cfg.template_key, ctx)
    subject = event_cfg.subject

    try:
        provider_id = await asyncio.to_thread(
            send_email,
            to_email=email,
            subject=subject,
            html_body=html_body,
        )
        log.status = "SENT" if provider_id != "skipped-local" else "SKIPPED"
        log.provider_message_id = provider_id
        log.sent_at = datetime.now(UTC).replace(tzinfo=None)
        log.error_message = None if log.status == "SENT" else "EMAIL_ENABLED=false"
    except Exception as exc:
        logger.exception("Email delivery failed for user %s event %s", user_id, event_key)
        log.status = "FAILED"
        log.error_message = str(exc)[:1000]

    await db.commit()
    await db.refresh(log)
    return log


async def create_notification_with_delivery(
    db: AsyncSession,
    payload: InternalNotificationCreate,
) -> Notification:
    notification_type = payload.notification_type.upper()
    if notification_type not in VALID_TYPES:
        notification_type = "ACCOUNT"

    notification = Notification(
        user_id=payload.user_id,
        notification_type=notification_type,
        title=payload.title,
        message=payload.message,
        status=UNREAD_STATUS,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        action_url=payload.action_url,
    )
    db.add(notification)
    await db.flush()

    if payload.send_in_app:
        db.add(
            NotificationDeliveryLog(
                notification_id=notification.notification_id,
                channel="IN_APP",
                delivery_status="DELIVERED",
            )
        )

    await db.commit()
    await db.refresh(notification)

    if payload.send_email:
        try:
            await dispatch_email(
                db,
                user_id=payload.user_id,
                recipient_email=payload.recipient_email,
                recipient_name=payload.recipient_name,
                event_type=payload.event_type or "GENERIC_NOTIFICATION",
                notification_type=notification_type,
                title=payload.title,
                message=payload.message,
                template_data=payload.template_data,
                related_entity_type=payload.related_entity_type,
                related_entity_id=payload.related_entity_id,
                action_url=payload.action_url,
                idempotency_key=payload.idempotency_key,
            )
        except Exception as exc:
            logger.warning("Email dispatch failed after in-app notification: %s", exc)

    return notification
