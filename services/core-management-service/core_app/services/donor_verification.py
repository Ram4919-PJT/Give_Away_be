from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.verification import VerificationRequest


class DonorNotVerifiedError(PermissionError):
    pass


async def is_donor_verified(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(
        select(VerificationRequest).where(
            VerificationRequest.user_id == user_id,
            VerificationRequest.request_type == "DONOR",
            VerificationRequest.status == "VERIFIED",
        )
    )
    return result.scalar_one_or_none() is not None


async def require_verified_donor(db: AsyncSession, user_id: int) -> None:
    if not await is_donor_verified(db, user_id):
        raise DonorNotVerifiedError(
            "Donor verification is required before submitting donation items."
        )
