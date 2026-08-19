from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from comm_app.dependencies.auth import TokenUser
from comm_app.models.notification import Notification, NotificationDeliveryLog, UserNotificationPreference
from comm_app.schemas.notification import (
    InternalNotificationCreate,
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationSummary,
)


READ_STATUS = "READ"
UNREAD_STATUS = "UNREAD"

VALID_TYPES = {"DONATION", "CAMPAIGN", "ACCOUNT", "SYSTEM", "APPLICATION"}


def _to_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse.model_validate(notification)


async def _summary_for_user(db: AsyncSession, user_id: int) -> NotificationSummary:
    base = select(Notification).where(Notification.user_id == user_id)
    all_count = await db.scalar(select(func.count()).select_from(base.subquery()))
    unread_count = await db.scalar(
        select(func.count()).select_from(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.status == UNREAD_STATUS)
            .subquery()
        )
    )

    async def type_count(notification_type: str) -> int:
        return await db.scalar(
            select(func.count()).select_from(
                select(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.notification_type == notification_type,
                )
                .subquery()
            )
        ) or 0

    donations = await type_count("DONATION")
    campaigns = await type_count("CAMPAIGN")
    applications = await type_count("APPLICATION")
    account = await type_count("ACCOUNT") + await type_count("SYSTEM")
    return NotificationSummary(
        all=all_count or 0,
        unread=unread_count or 0,
        donations=donations,
        campaigns=campaigns,
        account=account,
        applications=applications,
    )


async def create_notification(
    db: AsyncSession,
    payload: NotificationCreate | InternalNotificationCreate,
) -> Notification:
    from comm_app.services.notification_dispatch_service import create_notification_with_delivery

    if isinstance(payload, InternalNotificationCreate):
        return await create_notification_with_delivery(db, payload)

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
    db.add(
        NotificationDeliveryLog(
            notification_id=notification.notification_id,
            channel="IN_APP",
            delivery_status="DELIVERED",
        )
    )
    await db.commit()
    await db.refresh(notification)
    return notification


async def get_user_notifications(
    db: AsyncSession,
    user: TokenUser,
    *,
    status: str | None = None,
    notification_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    include_summary: bool = True,
) -> NotificationListResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    filters = [Notification.user_id == user.user_id]
    if status:
        normalized = status.upper()
        if normalized == "UNREAD":
            filters.append(Notification.status == UNREAD_STATUS)
        elif normalized == "READ":
            filters.append(Notification.status == READ_STATUS)
    if notification_type:
        normalized_type = notification_type.upper()
        if normalized_type == "ACCOUNT":
            filters.append(Notification.notification_type.in_(["ACCOUNT", "SYSTEM"]))
        elif normalized_type in VALID_TYPES:
            filters.append(Notification.notification_type == normalized_type)

    count_stmt = select(func.count()).select_from(Notification).where(*filters)
    total = await db.scalar(count_stmt) or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(Notification)
        .where(*filters)
        .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = [_to_response(row) for row in result.scalars().all()]
    summary = await _summary_for_user(db, user.user_id) if include_summary else NotificationSummary()
    return NotificationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        summary=summary,
    )


async def get_unread_count(db: AsyncSession, user: TokenUser) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.user_id, Notification.status == UNREAD_STATUS)
    )
    return count or 0


async def mark_as_read(db: AsyncSession, user: TokenUser, notification_id: int) -> NotificationResponse:
    result = await db.execute(
        select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.user_id == user.user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise LookupError("Notification not found")

    if notification.status != READ_STATUS:
        notification.status = READ_STATUS
        notification.read_at = datetime.now(UTC).replace(tzinfo=None)
        notification.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()
        await db.refresh(notification)
        await _decrement_unread_count(user.user_id)
    return _to_response(notification)


async def mark_all_as_read(db: AsyncSession, user: TokenUser) -> int:
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user.user_id,
            Notification.status == UNREAD_STATUS,
        )
    )
    rows = list(result.scalars().all())
    now = datetime.now(UTC).replace(tzinfo=None)
    for notification in rows:
        notification.status = READ_STATUS
        notification.read_at = now
        notification.updated_at = now
    await db.commit()
    return len(rows)


async def delete_notification(db: AsyncSession, user: TokenUser, notification_id: int) -> None:
    result = await db.execute(
        select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.user_id == user.user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise LookupError("Notification not found")
    await db.delete(notification)
    await db.commit()


async def list_preferences(db: AsyncSession, user: TokenUser) -> list[dict]:
    result = await db.execute(
        select(UserNotificationPreference).where(UserNotificationPreference.user_id == user.user_id)
    )
    return [
        {
            "preference_id": pref.preference_id,
            "user_id": pref.user_id,
            "channel": pref.channel,
            "is_enabled": pref.enabled,
            "updated_at": None,
        }
        for pref in result.scalars().all()
    ]


async def upsert_preference(db: AsyncSession, user: TokenUser, channel: str, is_enabled: bool) -> dict:
    result = await db.execute(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user.user_id,
            UserNotificationPreference.channel == channel,
        )
    )
    preference = result.scalar_one_or_none()
    if preference:
        preference.enabled = is_enabled
    else:
        preference = UserNotificationPreference(
            user_id=user.user_id,
            channel=channel,
            enabled=is_enabled,
        )
        db.add(preference)
    await db.commit()
    await db.refresh(preference)
    return {
        "preference_id": preference.preference_id,
        "user_id": preference.user_id,
        "channel": preference.channel,
        "is_enabled": preference.enabled,
        "updated_at": None,
    }


async def create_system_notification(
    db: AsyncSession,
    *,
    user_id: int,
    title: str,
    body: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        notification_type="SYSTEM",
        title=title,
        message=body,
        status=UNREAD_STATUS,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    await _increment_unread_count(user_id)
    return notification


async def _increment_unread_count(user_id: int) -> None:
    from shared.redis.client import get_redis, is_redis_enabled
    from shared.redis.keys import UNREAD_COUNT

    if not is_redis_enabled():
        return

    redis = get_redis()
    if redis is None:
        return

    await redis.incr(UNREAD_COUNT.format(user_id=str(user_id)))


async def _decrement_unread_count(user_id: int) -> None:
    from shared.redis.client import get_redis, is_redis_enabled
    from shared.redis.keys import UNREAD_COUNT

    if not is_redis_enabled():
        return

    redis = get_redis()
    if redis is None:
        return

    key = UNREAD_COUNT.format(user_id=str(user_id))
    value = await redis.decr(key)
    if value < 0:
        await redis.set(key, 0)

