"""Helpers for resolving the authenticated NGO profile."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.profiles import NgoProfile


async def get_ngo_profile_for_user(db: AsyncSession, user_id: int) -> NgoProfile | None:
    result = await db.execute(select(NgoProfile).where(NgoProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def require_ngo_profile(db: AsyncSession, user_id: int) -> NgoProfile:
    profile = await get_ngo_profile_for_user(db, user_id)
    if not profile:
        raise LookupError("NGO profile not found. Complete NGO registration first.")
    return profile


def is_ngo_verified(profile: NgoProfile) -> bool:
    status = (profile.verification_status or "").upper()
    return status in {"VERIFIED", "APPROVED"}


def is_ngo_suspended(profile: NgoProfile) -> bool:
    return (profile.verification_status or "").upper() == "SUSPENDED"


def is_ngo_operational_allowed(profile: NgoProfile) -> bool:
    return is_ngo_verified(profile) and not is_ngo_suspended(profile)
