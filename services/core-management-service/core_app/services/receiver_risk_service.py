"""Receiver verification risk checks — explainable flags for admin review."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.profiles import ReceiverProfile
from core_app.models.verification import VerificationRequest


def _norm_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _norm_digits(value: str | None) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _names_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return True
    return _norm_name(a) == _norm_name(b)


def compute_consistency_flags(payload: dict[str, Any] | None) -> list[str]:
    flags: list[str] = []
    if not payload:
        return ["MANUAL_REVIEW_REQUIRED"]

    personal = payload.get("personal") or {}
    identity = payload.get("identity") or {}
    address = payload.get("address") or {}
    beneficiary = payload.get("beneficiary") or {}
    bank = payload.get("bank") or {}

    personal_name = personal.get("full_name")
    identity_name = identity.get("full_name") or personal_name
    if personal_name and identity_name and not _names_match(personal_name, identity_name):
        flags.append("NAME_MISMATCH")

    if beneficiary.get("relationship") != "SELF" and beneficiary.get("full_name"):
        if personal_name and not _names_match(personal_name, beneficiary.get("full_name")):
            pass  # expected for third-party beneficiary
    elif beneficiary.get("relationship") == "SELF" and beneficiary.get("full_name"):
        if not _names_match(personal_name, beneficiary.get("full_name")):
            flags.append("BENEFICIARY_MISMATCH")

    bank_holder = bank.get("account_holder_name")
    if personal_name and bank_holder and not _names_match(personal_name, bank_holder):
        flags.append("BANK_NAME_MISMATCH")

    profile_addr = " ".join(
        filter(None, [personal.get("address_line"), personal.get("city"), personal.get("state")])
    )
    kyc_addr = " ".join(
        filter(None, [address.get("address_line"), address.get("city"), address.get("state")])
    )
    if profile_addr and kyc_addr and _norm_name(profile_addr) != _norm_name(kyc_addr):
        flags.append("ADDRESS_MISMATCH")

    if address.get("mismatch"):
        flags.append("ADDRESS_MISMATCH")

    return flags


def classify_risk_level(flags: list[str]) -> str:
    high_flags = {"DUPLICATE_BANK_ACCOUNT", "DUPLICATE_IDENTITY", "DOCUMENT_REUSE"}
    medium_flags = {
        "NAME_MISMATCH",
        "BANK_NAME_MISMATCH",
        "ADDRESS_MISMATCH",
        "BENEFICIARY_MISMATCH",
        "DOCUMENT_INCONSISTENCY",
    }
    if any(f in high_flags for f in flags):
        return "HIGH"
    if any(f in medium_flags for f in flags):
        return "MEDIUM"
    if flags:
        return "LOW"
    return "LOW"


async def detect_duplicate_flags(
    db: AsyncSession,
    *,
    user_id: int,
    payload: dict[str, Any] | None,
) -> list[str]:
    flags: list[str] = []
    if not payload:
        return flags

    bank = payload.get("bank") or {}
    identity = payload.get("identity") or {}
    account = _norm_digits(bank.get("account_number"))
    ifsc = str(bank.get("ifsc") or "").strip().upper()
    id_number = _norm_digits(identity.get("id_number"))

    if account and ifsc:
        bank_hash = _hash_value(f"{account}:{ifsc}")
        result = await db.execute(
            select(VerificationRequest).where(
                VerificationRequest.request_type == "RECEIVER",
                VerificationRequest.user_id != user_id,
            )
        )
        for req in result.scalars().all():
            other_bank = (req.payload or {}).get("bank") or {}
            other_account = _norm_digits(other_bank.get("account_number"))
            other_ifsc = str(other_bank.get("ifsc") or "").strip().upper()
            if other_account and other_ifsc and _hash_value(f"{other_account}:{other_ifsc}") == bank_hash:
                flags.append("DUPLICATE_BANK_ACCOUNT")
                break

    if id_number:
        id_hash = _hash_value(id_number)
        result = await db.execute(
            select(VerificationRequest).where(
                VerificationRequest.request_type == "RECEIVER",
                VerificationRequest.user_id != user_id,
            )
        )
        for req in result.scalars().all():
            other_id = _norm_digits((req.payload or {}).get("identity", {}).get("id_number"))
            if other_id and _hash_value(other_id) == id_hash:
                flags.append("DUPLICATE_IDENTITY")
                break

    mobile = _norm_digits((payload.get("personal") or {}).get("mobile"))
    if mobile:
        result = await db.execute(
            select(ReceiverProfile).where(
                ReceiverProfile.user_id != user_id,
                ReceiverProfile.mobile == mobile,
            )
        )
        if result.scalar_one_or_none():
            flags.append("DUPLICATE_MOBILE")

    return flags


async def evaluate_receiver_risk(
    db: AsyncSession,
    *,
    user_id: int,
    payload: dict[str, Any] | None,
) -> tuple[list[str], str]:
    flags = compute_consistency_flags(payload)
    flags.extend(await detect_duplicate_flags(db, user_id=user_id, payload=payload))
    flags = list(dict.fromkeys(flags))
    if not flags:
        flags.append("MANUAL_REVIEW_REQUIRED")
    return flags, classify_risk_level(flags)
