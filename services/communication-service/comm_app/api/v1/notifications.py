from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from comm_app.config import settings
from comm_app.db.session import get_db
from comm_app.dependencies.auth import TokenUser, get_current_user
from comm_app.schemas.notification import (
    EmailOnlyDispatch,
    InternalNotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationSummary,
    PreferenceResponse,
    PreferenceUpdate,
)
from comm_app.services import notification_service
from comm_app.services.notification_dispatch_service import dispatch_email

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _verify_internal_key(x_internal_key: str | None) -> None:
    if not x_internal_key or x_internal_key != settings.INTERNAL_NOTIFICATION_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal key")


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    status: str | None = Query(default=None, description="READ or UNREAD"),
    type: str | None = Query(default=None, alias="type", description="DONATION, CAMPAIGN, ACCOUNT"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.get_user_notifications(
        db,
        user,
        status=status,
        notification_type=type,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=NotificationSummary)
async def get_notification_summary(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service._summary_for_user(db, user.user_id)


@router.get("/unread-count")
async def get_unread_count(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = await notification_service.get_unread_count(db, user)
    return {"unread_count": count}


@router.patch("/read-all")
async def mark_all_notifications_read(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await notification_service.mark_all_as_read(db, user)
    return {"updated": updated}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await notification_service.mark_as_read(db, user, notification_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await notification_service.delete_notification(db, user, notification_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/internal/email", status_code=status.HTTP_201_CREATED)
async def dispatch_internal_email(
    payload: EmailOnlyDispatch,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
):
    """Email-only dispatch for transactional messages (e.g. OTP)."""
    _verify_internal_key(x_internal_key)
    log = await dispatch_email(
        db,
        user_id=payload.user_id,
        recipient_email=payload.recipient_email,
        recipient_name=payload.recipient_name,
        event_type=payload.event_type,
        notification_type=payload.notification_type,
        title=payload.title,
        message=payload.message,
        template_data=payload.template_data,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        action_url=payload.action_url,
        idempotency_key=payload.idempotency_key,
    )
    return {
        "status": log.status,
        "recipient_email": log.recipient_email,
        "idempotency_key": log.idempotency_key,
        "error_message": log.error_message,
    }


@router.post("/internal", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_internal_notification(
    payload: InternalNotificationCreate,
    db: AsyncSession = Depends(get_db),
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
):
    """Service-to-service notification creation. Not for browser clients."""
    _verify_internal_key(x_internal_key)
    notification = await notification_service.create_notification(db, payload)
    return NotificationResponse.model_validate(notification)


@router.get("/preferences", response_model=list[PreferenceResponse])
async def list_notification_preferences(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.list_preferences(db, user)


@router.put("/preferences", response_model=PreferenceResponse)
async def update_notification_preferences(
    payload: PreferenceUpdate,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.upsert_preference(
        db, user, channel=payload.channel, is_enabled=payload.is_enabled
    )
