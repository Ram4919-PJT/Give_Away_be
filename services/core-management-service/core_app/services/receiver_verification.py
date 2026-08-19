from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.verification import VerificationRequest


class ReceiverNotVerifiedError(PermissionError):
    pass


async def is_receiver_verified(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(
        select(VerificationRequest).where(
            VerificationRequest.user_id == user_id,
            VerificationRequest.request_type == "RECEIVER",
            VerificationRequest.status == "VERIFIED",
        )
    )
    return result.scalar_one_or_none() is not None


async def require_verified_receiver(db: AsyncSession, user_id: int) -> None:
    if not await is_receiver_verified(db, user_id):
        raise ReceiverNotVerifiedError(
            "Receiver verification is required before creating or managing item requests."
        )
