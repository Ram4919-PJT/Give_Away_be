from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from comm_app.db.session import get_db
from comm_app.models.notification import Notification, NotificationDeliveryLog, NotificationTemplate, UserNotificationPreference

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str


class TemplateCreate(BaseModel):
    template_name: str
    channel: str
    content: str


@router.get("")
async def list_notifications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification))
    return result.scalars().all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_notification(data: NotificationCreate, db: AsyncSession = Depends(get_db)):
    notif = Notification(
        user_id=data.user_id,
        title=data.title,
        message=data.message,
        status="UNREAD",
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    
    log = NotificationDeliveryLog(notification_id=notif.notification_id, channel="IN_APP", delivery_status="DELIVERED")
    db.add(log)
    await db.commit()
    return notif


@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.notification_id == notification_id))
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail=f"Notification #{notification_id} not found")
    notif.status = "READ"
    await db.commit()
    return notif


@router.get("/templates")
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationTemplate))
    return result.scalars().all()


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(data: TemplateCreate, db: AsyncSession = Depends(get_db)):
    tmpl = NotificationTemplate(template_name=data.template_name, channel=data.channel, content=data.content)
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/logs")
async def list_delivery_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NotificationDeliveryLog))
    return result.scalars().all()


@router.get("/preferences")
async def list_preferences(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserNotificationPreference))
    return result.scalars().all()
