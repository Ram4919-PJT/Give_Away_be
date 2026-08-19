"""FastAPI dependencies for NGO verification-based access control."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.models.profiles import NgoProfile
from core_app.services.ngo_service import (
    is_ngo_suspended,
    is_ngo_verified,
    require_ngo_profile,
)

VERIFIED_ONLY_DETAIL = "This feature is available only after your NGO is verified."
SUSPENDED_DETAIL = "Your NGO account is suspended. Contact platform support for assistance."


async def require_ngo_profile_dep(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("NGO")),
) -> NgoProfile:
    try:
        return await require_ngo_profile(db, user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


async def require_verified_ngo_profile(
    profile: NgoProfile = Depends(require_ngo_profile_dep),
) -> NgoProfile:
    if is_ngo_suspended(profile):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SUSPENDED_DETAIL)
    if not is_ngo_verified(profile):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=VERIFIED_ONLY_DETAIL)
    return profile
