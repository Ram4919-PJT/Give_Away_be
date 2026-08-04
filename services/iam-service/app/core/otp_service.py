import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ConflictError, NotFoundError, RateLimitError
from shared.redis.keys import OTP_RATE
from shared.redis.rate_limit import is_rate_limited
from app.events.publishers import EventPublisher
from app.models.enums import OtpPurpose, OtpVerificationStatus
from app.models.otp_verification import OtpVerification
from app.repositories.otp_repository import OtpRepository
from app.repositories.user_repository import UserRepository
from app.schemas.otp import OtpSendRequest, OtpVerifyRequest


class OtpService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.otp_repo = OtpRepository(db)
        self.user_repo = UserRepository(db)

    async def send_otp(self, data: OtpSendRequest) -> None:
        from gateway.config import settings

        user = await self._resolve_user(data.email, data.mobile)
        if not user:
            raise NotFoundError("User not found")

        identifier = (data.email or data.mobile or str(user.user_id)).lower()
        rate_key = OTP_RATE.format(identifier=identifier)
        if await is_rate_limited(
            rate_key,
            max_attempts=settings.REDIS_OTP_RATE_LIMIT,
            window_seconds=settings.REDIS_OTP_RATE_WINDOW,
        ):
            raise RateLimitError("Too many OTP requests. Please try again later.")

        pending_count = await self.otp_repo.count_pending(user.user_id)
        if pending_count >= settings.OTP_MAX_PENDING:
            raise ConflictError("Too many pending OTP requests")

        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp = OtpVerification(
            user_id=user.user_id,
            otp_code=self._hash_otp(otp_code),
            purpose=data.purpose,
            expires_at=expires_at,
            verified_status=OtpVerificationStatus.PENDING,
        )
        await self.otp_repo.create(otp)
        await self.db.commit()

        if settings.OTP_LOG_TO_CONSOLE or settings.ENV == "development":
            print(
                f"[DEV OTP] user={user.user_id} code={otp_code} purpose={data.purpose.value}"
            )

        await EventPublisher.publish(
            "otp.sent",
            {
                "user_id": str(user.user_id),
                "purpose": data.purpose.value,
            },
        )

    async def verify_otp(self, data: OtpVerifyRequest) -> None:
        user = await self._resolve_user(data.email, data.mobile)
        if not user:
            raise NotFoundError("User not found")

        otp = await self.otp_repo.get_by_code_hash(
            user_id=user.user_id,
            otp_code_hash=self._hash_otp(data.otp_code),
            purpose=data.purpose,
        )
        if not otp:
            raise ConflictError("Invalid OTP")

        if otp.expires_at < datetime.now(UTC):
            await self.otp_repo.update_status(otp, OtpVerificationStatus.EXPIRED)
            await self.db.commit()
            raise ConflictError("OTP has expired")

        await self.otp_repo.update_status(otp, OtpVerificationStatus.VERIFIED)
        await self.db.commit()

    async def _resolve_user(
        self, email: str | None, mobile: str | None
    ):
        if email:
            return await self.user_repo.get_by_email(email)
        if mobile:
            return await self.user_repo.get_by_mobile(mobile)
        return None

    @staticmethod
    def _hash_otp(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()
