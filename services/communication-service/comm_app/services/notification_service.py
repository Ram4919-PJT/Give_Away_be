from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comm_app.core.exceptions import NotFoundError
from comm_app.dependencies.auth import TokenUser
from comm_app.models.enums import NotificationStatus
from comm_app.models.notification import Notification, UserNotificationPreference
from comm_app.schemas.notification import NotificationCreate, PreferenceUpdate


async def list_notifications(db: AsyncSession, user: TokenUser) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.user_id)
        .order_by(Notification.created_at.desc())
    )
    return list(result.scalars().all())


async def mark_notification_read(
    db: AsyncSession, user: TokenUser, notification_id: UUID
) -> Notification:
    result = await db.execute(
        select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.user_id == user.user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundError("Notification not found")

    notification.status = NotificationStatus.READ
    notification.read_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(notification)
    return notification


async def create_notification(
    db: AsyncSession, payload: NotificationCreate
) -> Notification:
    notification = Notification(
        user_id=payload.user_id,
        title=payload.title,
        body=payload.body,
        channel=payload.channel,
        status=NotificationStatus.SENT,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def list_preferences(db: AsyncSession, user: TokenUser) -> list[UserNotificationPreference]:
    result = await db.execute(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user.user_id
        )
    )
    return list(result.scalars().all())


async def upsert_preference(
    db: AsyncSession, user: TokenUser, payload: PreferenceUpdate
) -> UserNotificationPreference:
    result = await db.execute(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user.user_id,
            UserNotificationPreference.channel == payload.channel,
        )
    )
    preference = result.scalar_one_or_none()
    if preference:
        preference.is_enabled = payload.is_enabled
    else:
        preference = UserNotificationPreference(
            user_id=user.user_id,
            channel=payload.channel,
            is_enabled=payload.is_enabled,
        )
        db.add(preference)

    await db.commit()
    await db.refresh(preference)
    return preference
