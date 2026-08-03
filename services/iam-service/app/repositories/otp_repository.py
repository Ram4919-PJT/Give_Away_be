from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OtpPurpose, OtpVerificationStatus
from app.models.otp_verification import OtpVerification
from app.repositories.base import BaseRepository


class OtpRepository(BaseRepository[OtpVerification]):
    model = OtpVerification

    async def create(self, otp: OtpVerification) -> OtpVerification:
        return await super().create(otp)

    async def get_by_code_hash(
        self,
        *,
        user_id: uuid.UUID,
        otp_code_hash: str,
        purpose: OtpPurpose,
    ) -> OtpVerification | None:
        stmt = select(OtpVerification).where(
            OtpVerification.user_id == user_id,
            OtpVerification.otp_code == otp_code_hash,
            OtpVerification.purpose == purpose,
            OtpVerification.verified_status == OtpVerificationStatus.PENDING,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_pending(
        self,
        *,
        user_id: uuid.UUID,
        purpose: OtpPurpose,
    ) -> OtpVerification | None:
        stmt = (
            select(OtpVerification)
            .where(
                OtpVerification.user_id == user_id,
                OtpVerification.purpose == purpose,
                OtpVerification.verified_status == OtpVerificationStatus.PENDING,
            )
            .order_by(OtpVerification.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        otp: OtpVerification,
        status: OtpVerificationStatus,
    ) -> OtpVerification:
        otp.verified_status = status
        await self.session.flush()
        await self.session.refresh(otp)
        return otp

    async def count_pending(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(OtpVerification)
            .where(
                OtpVerification.user_id == user_id,
                OtpVerification.verified_status == OtpVerificationStatus.PENDING,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_expired(self) -> int:
        stmt = (
            delete(OtpVerification)
            .where(
                OtpVerification.expires_at < datetime.now(UTC),
                OtpVerification.verified_status == OtpVerificationStatus.PENDING,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0
