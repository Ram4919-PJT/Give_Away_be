"""Load verified KYC bank/payment details for a receiver user."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.verification import VerificationRequest
from core_app.services.kyc.masking import mask_bank_account


async def get_receiver_kyc_payout_info(db: AsyncSession, user_id: int) -> dict | None:
    result = await db.execute(
        select(VerificationRequest)
        .where(
            VerificationRequest.user_id == user_id,
            VerificationRequest.request_type == "RECEIVER",
        )
        .order_by(VerificationRequest.request_id.desc())
        .limit(1)
    )
    req = result.scalar_one_or_none()
    if not req or not req.payload:
        return None

    payload = req.payload
    bank = payload.get("bank") or {}
    payment = payload.get("payment_destination") or {}
    dest_type = payment.get("type") or "RECEIVER_BANK"

    account_number = bank.get("account_number") or ""
    if not bank.get("account_holder_name") or not account_number or not bank.get("ifsc"):
        return None

    return {
        "payment_destination_type": dest_type,
        "bank_account_holder": bank.get("account_holder_name"),
        "bank_name": bank.get("bank_name"),
        "bank_ifsc": str(bank.get("ifsc", "")).strip().upper(),
        "bank_account_last4": account_number[-4:] if len(account_number) >= 4 else account_number,
        "institution_name": payment.get("institution_name"),
        "kyc_verification_id": req.request_id,
        "kyc_reference": req.reference_code,
        "masked_account": mask_bank_account(account_number),
    }
