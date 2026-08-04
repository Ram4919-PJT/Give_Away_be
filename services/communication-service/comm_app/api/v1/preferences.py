from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from comm_app.db.session import get_db
from comm_app.dependencies.auth import TokenUser, get_current_user
from comm_app.schemas.notification import PreferenceResponse, PreferenceUpdate
from comm_app.services import notification_service

router = APIRouter(prefix="/preferences", tags=["Notification Preferences"])


@router.get("", response_model=list[PreferenceResponse])
async def list_preferences(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.list_preferences(db, user)


@router.put("", response_model=PreferenceResponse)
async def upsert_preference(
    payload: PreferenceUpdate,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await notification_service.upsert_preference(db, user, payload)
