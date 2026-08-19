from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.services.donor_settings_service import get_donor_settings, update_donor_settings

router = APIRouter(tags=["Donor Settings"])


class DonorSettingsUpdate(BaseModel):
    anonymousDonations: bool | None = None
    preferredCategories: list[str] | None = None
    language: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=64)
    dateFormat: str | None = Field(default=None, max_length=20)
    theme: str | None = Field(default=None, max_length=20)
    donationUpdates: bool | None = None
    impactReports: bool | None = None
    marketingEmails: bool | None = None


@router.get("/donors/me/settings")
async def read_my_donor_settings(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await get_donor_settings(db, user_id=user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/donors/me/settings")
async def patch_my_donor_settings(
    payload: DonorSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    data: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not data:
        try:
            return await get_donor_settings(db, user_id=user.user_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        return await update_donor_settings(db, user_id=user.user_id, payload=data)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
