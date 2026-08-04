from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from comm_app.db.session import get_db
from comm_app.dependencies.auth import TokenUser, get_current_user, require_roles
from comm_app.schemas.notification import NotificationCreate, NotificationResponse
from comm_app.services import notification_service

router = APIRouter(tags=["Notifications"])


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.list_notifications(db, user)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: UUID,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.mark_notification_read(db, user, notification_id)


@router.post("/", response_model=NotificationResponse, status_code=201)
async def create_notification(
    payload: NotificationCreate,
    _user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.create_notification(db, payload)
