"""Mobile OTP for receiver KYC — hashed codes only, never stored in plain text."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.config import settings
from core_app.models.verification import KycMobileOtp


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _resend_cooldown_seconds() -> int:
    if settings.ENV != "production" or settings.DEBUG:
        return min(settings.KYC_MOBILE_OTP_RESEND_COOLDOWN_SEC, 15)
    return settings.KYC_MOBILE_OTP_RESEND_COOLDOWN_SEC


def _is_production() -> bool:
    return settings.ENV == "production" and not settings.DEBUG


async def send_mobile_otp(db: AsyncSession, *, user_id: int, mobile: str) -> tuple[bool, str | None]:
    """Send OTP. Returns (issued_new_code, dev_plain_code_for_logging_only)."""
    mobile_digits = "".join(c for c in mobile if c.isdigit())
    if len(mobile_digits) < 10:
        raise ValueError("Invalid mobile number")
    mobile_digits = mobile_digits[-10:]

    recent = await db.execute(
        select(KycMobileOtp)
        .where(
            KycMobileOtp.user_id == user_id,
            KycMobileOtp.verified_at.is_(None),
        )
        .order_by(KycMobileOtp.created_at.desc())
        .limit(1)
    )
    last = recent.scalar_one_or_none()

    if last and last.created_at:
        cooldown = timedelta(seconds=_resend_cooldown_seconds())
        elapsed = _now() - last.created_at.replace(tzinfo=None)
        if elapsed < cooldown:
            if _is_production():
                if settings.ENV != "production" or settings.DEBUG:
                    print(
                        f"[DEV KYC OTP] active OTP still valid for user={user_id} "
                        f"mobile=***{mobile_digits[-4:]} — enter existing code or wait "
                        f"{int(cooldown.total_seconds() - elapsed.total_seconds())}s to resend"
                    )
                return False, None
            # Development: replace stale OTP so testers always get a fresh console code
            await db.execute(
                delete(KycMobileOtp).where(
                    KycMobileOtp.user_id == user_id,
                    KycMobileOtp.verified_at.is_(None),
                )
            )

    code = f"{secrets.randbelow(10_000):04d}"
    expires = _now() + timedelta(minutes=settings.KYC_MOBILE_OTP_EXPIRE_MINUTES)
    row = KycMobileOtp(
        user_id=user_id,
        mobile=mobile_digits,
        otp_hash=_hash_otp(code),
        expires_at=expires,
        attempts=0,
    )
    db.add(row)
    await db.commit()

    if settings.ENV != "production" or settings.DEBUG:
        print(f"[DEV KYC OTP] user={user_id} mobile=***{mobile_digits[-4:]} code={code}")

    return True, code if (settings.ENV != "production" or settings.DEBUG) else None


async def verify_mobile_otp(db: AsyncSession, *, user_id: int, mobile: str, otp_code: str) -> datetime:
    mobile_digits = "".join(c for c in mobile if c.isdigit())[-10:]
    normalized_code = "".join(c for c in str(otp_code or "") if c.isdigit())

    if len(normalized_code) < 4:
        raise PermissionError("Enter the 4-digit OTP")

    result = await db.execute(
        select(KycMobileOtp)
        .where(
            KycMobileOtp.user_id == user_id,
            KycMobileOtp.mobile == mobile_digits,
            KycMobileOtp.verified_at.is_(None),
        )
        .order_by(KycMobileOtp.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()

    if not row:
        # Fallback: latest unverified OTP for user (mobile formatting mismatch)
        fallback = await db.execute(
            select(KycMobileOtp)
            .where(
                KycMobileOtp.user_id == user_id,
                KycMobileOtp.verified_at.is_(None),
            )
            .order_by(KycMobileOtp.created_at.desc())
            .limit(1)
        )
        row = fallback.scalar_one_or_none()

    if not row:
        raise LookupError("No active OTP found. Tap Send OTP first.")

    if row.expires_at.replace(tzinfo=None) < _now():
        raise PermissionError("OTP has expired. Request a new code.")

    if row.attempts >= settings.KYC_MOBILE_OTP_MAX_ATTEMPTS:
        raise PermissionError("Maximum OTP attempts exceeded. Request a new code.")

    row.attempts += 1
    if row.otp_hash != _hash_otp(normalized_code):
        await db.commit()
        raise PermissionError("Invalid OTP. Please check and try again.")

    verified_at = _now()
    row.verified_at = verified_at
    await db.commit()
    return verified_at
