from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.profiles import DonorProfile

DEFAULT_DONOR_SETTINGS: dict[str, Any] = {
    "anonymousDonations": False,
    "preferredCategories": [],
    "language": "en-IN",
    "timezone": "Asia/Kolkata",
    "dateFormat": "DD/MM/YYYY",
    "theme": "light",
    "donationUpdates": True,
    "impactReports": True,
    "marketingEmails": False,
}

ALLOWED_KEYS = set(DEFAULT_DONOR_SETTINGS.keys())


async def _get_donor_profile(db: AsyncSession, user_id: int) -> DonorProfile:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    donor = result.scalar_one_or_none()
    if donor is None:
        raise LookupError("Donor profile not found")
    return donor


def _merge_settings(stored: dict[str, Any] | None) -> dict[str, Any]:
    merged = {**DEFAULT_DONOR_SETTINGS}
    if stored:
        for key in ALLOWED_KEYS:
            if key in stored:
                merged[key] = stored[key]
    return merged


async def get_donor_settings(db: AsyncSession, *, user_id: int) -> dict[str, Any]:
    donor = await _get_donor_profile(db, user_id)
    return _merge_settings(donor.preferences)


async def update_donor_settings(
    db: AsyncSession,
    *,
    user_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    donor = await _get_donor_profile(db, user_id)
    current = _merge_settings(donor.preferences)

    for key, value in payload.items():
        if key not in ALLOWED_KEYS:
            continue
        if key == "preferredCategories" and not isinstance(value, list):
            continue
        current[key] = value

    donor.preferences = current
    await db.commit()
    await db.refresh(donor)
    return current
