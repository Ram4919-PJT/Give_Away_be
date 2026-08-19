"""Single source of truth for receiver money-request eligibility."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.profiles import ReceiverProfile
from core_app.models.verification import VerificationDocument, VerificationRequest
from core_app.services.kyc.receiver_document_config import (
    RECEIVER_PROGRESS_STEPS,
    get_all_required_document_types,
)

BLOCKING_FLAGS = frozenset({"DUPLICATE_BANK_ACCOUNT", "DUPLICATE_IDENTITY"})
TERMINAL_BLOCK_STATUSES = frozenset({"SUSPENDED", "REJECTED"})
REVIEW_COMPLETE_STATUSES = frozenset({"VERIFIED"})


def _section_complete(payload: dict, key: str, fields: list[str]) -> bool:
    section = payload.get(key) or {}
    return all(str(section.get(f) or "").strip() for f in fields)


def compute_kyc_progress(
    *,
    payload: dict | None,
    documents: list[dict] | None,
    profile_status: str,
    request_status: str | None,
) -> dict[str, Any]:
    payload = payload or {}
    uploaded = {d["document_type"] for d in (documents or [])}
    mobile = payload.get("mobile_verification") or {}
    identity = payload.get("identity") or {}

    steps = {
        "CONTACT": bool(mobile.get("verified_at")) or _section_complete(
            payload, "personal", ["mobile", "email"]
        ),
        "IDENTITY": bool(identity.get("submitted_at") or identity.get("id_type")) and "ID_FRONT" in uploaded,
        "ADDRESS": _section_complete(payload, "address", ["address_line", "city", "state", "pincode"])
        or _section_complete(payload, "personal", ["address_line", "city", "state", "pincode"]),
        "BENEFICIARY": bool((payload.get("beneficiary") or {}).get("relationship")),
        "SUPPORTING_DOCUMENTS": bool((payload.get("assistance") or {}).get("category")),
        "BANK": _section_complete(payload, "bank", ["account_holder_name", "account_number", "ifsc"]),
        "ADMIN_REVIEW": profile_status in REVIEW_COMPLETE_STATUSES
        or request_status in {"UNDER_REVIEW", "DOCUMENTS_SUBMITTED", "VALIDATION_IN_PROGRESS", "VERIFIED"},
    }

    completed = [s["id"] for s in RECEIVER_PROGRESS_STEPS if steps.get(s["id"])]
    pending = [s["id"] for s in RECEIVER_PROGRESS_STEPS if not steps.get(s["id"])]
    total = len(RECEIVER_PROGRESS_STEPS)
    percent = round((len(completed) / total) * 100) if total else 0

    return {
        "steps": steps,
        "completed": completed,
        "pending": pending,
        "percent": percent,
        "labels": {s["id"]: s["label"] for s in RECEIVER_PROGRESS_STEPS},
    }


async def can_receiver_request_money(db: AsyncSession, user_id: int) -> dict[str, Any]:
    reasons: list[str] = []
    missing_steps: list[str] = []
    blocking_flags: list[str] = []

    profile_row = await db.execute(
        select(ReceiverProfile).where(ReceiverProfile.user_id == user_id)
    )
    profile = profile_row.scalar_one_or_none()
    if not profile:
        return {
            "eligible": False,
            "can_request_assistance": False,
            "block_reason_code": "KYC_REQUIRED",
            "reasons": ["Receiver profile not found"],
            "missing_steps": ["PROFILE"],
            "blocking_flags": [],
            "progress": None,
            "profile_status": None,
            "request_status": None,
        }

    status = (profile.verification_status or "REGISTERED").upper()
    if status in TERMINAL_BLOCK_STATUSES:
        reasons.append("Account verification is not approved" if status == "REJECTED" else "Account is suspended")
        return {
            "eligible": False,
            "can_request_assistance": False,
            "block_reason_code": "ACCOUNT_SUSPENDED" if status == "SUSPENDED" else "VERIFICATION_REJECTED",
            "reasons": reasons,
            "missing_steps": [],
            "blocking_flags": ["ACCOUNT_SUSPENDED"] if status == "SUSPENDED" else ["VERIFICATION_REJECTED"],
            "progress": None,
            "profile_status": status,
            "request_status": None,
        }

    req_row = await db.execute(
        select(VerificationRequest)
        .where(
            VerificationRequest.user_id == user_id,
            VerificationRequest.request_type == "RECEIVER",
        )
        .order_by(VerificationRequest.request_id.desc())
        .limit(1)
    )
    req = req_row.scalar_one_or_none()
    payload = (req.payload if req else None) or {}
    doc_rows = []
    if req:
        doc_result = await db.execute(
            select(VerificationDocument).where(VerificationDocument.request_id == req.request_id)
        )
        doc_rows = [
            {"document_type": d.document_type, "verification_status": d.verification_status}
            for d in doc_result.scalars().all()
        ]

    progress = compute_kyc_progress(
        payload=payload,
        documents=doc_rows,
        profile_status=status,
        request_status=req.status if req else None,
    )

    pending_admin_requests: list[dict] = []
    if status != "VERIFIED":
        reasons.append("Verification must be approved by admin")
        missing_steps.extend(progress["pending"])

        if not (payload.get("mobile_verification") or {}).get("verified_at"):
            reasons.append("Mobile verification pending")
            if "CONTACT" not in missing_steps:
                missing_steps.append("CONTACT")

        required_docs = get_all_required_document_types(payload)
        uploaded_types = {d["document_type"] for d in doc_rows}
        for doc_type in required_docs:
            if doc_type not in uploaded_types:
                reasons.append(f"Required document missing: {doc_type.replace('_', ' ').title()}")
                if "SUPPORTING_DOCUMENTS" not in missing_steps:
                    missing_steps.append("SUPPORTING_DOCUMENTS")

        rejected_docs = [d for d in doc_rows if d.get("verification_status") == "REJECTED"]
        if rejected_docs:
            reasons.append("Some documents were rejected and need re-upload")

        bank = payload.get("bank") or {}
        if not all(bank.get(k) for k in ("account_holder_name", "account_number", "ifsc")):
            reasons.append("Bank verification incomplete")
            if "BANK" not in missing_steps:
                missing_steps.append("BANK")

        pending_admin_requests = [
            r for r in (payload.get("admin_document_requests") or [])
            if r.get("status") in (None, "PENDING", "MORE_INFORMATION_REQUIRED")
        ]
        if pending_admin_requests:
            reasons.append("Additional documents requested by admin")
            missing_steps.append("SUPPORTING_DOCUMENTS")

    risk_flags = (req.risk_flags if req else None) or []
    blocking_flags = [f for f in risk_flags if f in BLOCKING_FLAGS]
    if blocking_flags:
        reasons.append("Additional compliance review is required")

    eligible = status == "VERIFIED" and not reasons

    block_reason_code: str | None = None
    if not eligible:
        if status == "SUSPENDED":
            block_reason_code = "ACCOUNT_SUSPENDED"
        elif status == "REJECTED":
            block_reason_code = "VERIFICATION_REJECTED"
        elif pending_admin_requests or status == "MORE_DOCUMENTS_REQUIRED":
            block_reason_code = "ACTION_REQUIRED"
        elif status in {"UNDER_REVIEW", "DOCUMENTS_SUBMITTED", "VALIDATION_IN_PROGRESS"}:
            block_reason_code = "KYC_UNDER_REVIEW"
        else:
            block_reason_code = "KYC_REQUIRED"

    return {
        "eligible": eligible,
        "can_request_assistance": eligible,
        "block_reason_code": block_reason_code,
        "reasons": list(dict.fromkeys(reasons)),
        "missing_steps": list(dict.fromkeys(missing_steps)),
        "blocking_flags": blocking_flags,
        "progress": progress,
        "profile_status": status,
        "request_status": req.status if req else None,
    }
