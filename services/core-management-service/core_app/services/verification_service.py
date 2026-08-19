from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core_app.config import settings
from core_app.core.exceptions import KycValidationError
from core_app.integrations.notification_client import notify_user
from core_app.models.profiles import DonorProfile, NgoProfile, ReceiverProfile
from core_app.models.verification import (
    RejectionReason,
    VerificationAuditLog,
    VerificationDocument,
    VerificationRequest,
    VerificationStatusHistory,
)
from core_app.services.kyc.masking import looks_masked_value, mask_document_number, mask_payload_sensitive
from core_app.services.kyc.donor_document_config import (
    DONOR_ALLOWED_DOCUMENT_TYPES,
    build_donor_verification_config_response,
)
from core_app.services.kyc.donor_kyc_validation import build_donor_readiness_response, validate_donor_verification_submission
from core_app.services.kyc.receiver_kyc_validation import build_kyc_readiness_response, validate_receiver_kyc_submission
from core_app.services.kyc.provider import get_kyc_provider
from core_app.services.kyc_document_storage import delete_storage_file, save_kyc_document
from core_app.services.receiver_risk_service import evaluate_receiver_risk
from core_app.utils.portal_urls import (
    admin_assistance_review_url,
    admin_item_verification_url,
    admin_kyc_review_url,
)

logger = logging.getLogger(__name__)

ROLE_TO_REQUEST_TYPE = {
    "NGO": "NGO",
    "RECEIVER": "RECEIVER",
    "DONOR": "DONOR",
}

EDITABLE_STATUSES = {"DRAFT", "REJECTED", "MORE_DOCUMENTS_REQUIRED", "KYC_IN_PROGRESS"}
SUBMITTED_STATUSES = {"DOCUMENTS_SUBMITTED", "UNDER_REVIEW", "VALIDATION_IN_PROGRESS"}
TERMINAL_REQUEST_STATUSES = {"VERIFIED", "SUSPENDED"}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _reference_code(request_id: int) -> str:
    return f"VER-{request_id:06d}"


def _ngo_risk_flags(payload: dict[str, Any] | None) -> tuple[list[str], str]:
    flags: list[str] = []
    if not payload:
        return ["MANUAL_REVIEW_REQUIRED"], "LOW"
    org = payload.get("organization") or {}
    bank = payload.get("bank") or {}
    org_name = org.get("ngo_name") or payload.get("ngo_name") or ""
    account_name = bank.get("account_holder_name") or ""
    if org_name and account_name and org_name.strip().lower() != account_name.strip().lower():
        flags.append("BANK_NAME_MISMATCH")
    if not flags:
        flags.append("MANUAL_REVIEW_REQUIRED")
    level = "MEDIUM" if "BANK_NAME_MISMATCH" in flags else "LOW"
    return flags, level


async def _apply_identity_verification(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Run configured KYC provider for receiver identity; update payload in place."""
    payload = dict(payload or {})
    identity = dict(payload.get("identity") or {})
    personal = dict(payload.get("personal") or {})

    id_number = identity.get("id_number") or ""
    id_type = identity.get("id_type") or ""
    if not id_number or not id_type:
        identity["provider_status"] = "PENDING_MANUAL"
        payload["identity"] = identity
        return payload

    provider = get_kyc_provider()
    result = await provider.verify_identity(
        document_type=id_type,
        document_number=id_number,
        full_name=personal.get("full_name") or identity.get("full_name"),
        dob=personal.get("dob"),
    )
    identity["provider"] = result.provider
    identity["provider_ref"] = result.reference
    identity["provider_status"] = "VERIFIED" if result.verified else "PENDING_MANUAL"
    identity["provider_message"] = result.message
    identity["submitted_at"] = _now().isoformat()
    if result.verified_at:
        identity["verified_at"] = result.verified_at.isoformat()
    identity["id_number_masked"] = mask_document_number(id_type, id_number)
    # Keep full number only in payload for risk checks during submit; masked on API responses
    payload["identity"] = identity
    return payload


async def _record_history(
    db: AsyncSession,
    request_id: int,
    status: str,
    *,
    note: str | None = None,
    changed_by: int | None = None,
) -> None:
    db.add(
        VerificationStatusHistory(
            request_id=request_id,
            status=status,
            note=note,
            changed_by=changed_by,
        )
    )


async def _audit(
    db: AsyncSession,
    *,
    admin_user_id: int,
    request_id: int,
    action: str,
    old_status: str | None,
    new_status: str | None,
    reason: str | None = None,
) -> None:
    db.add(
        VerificationAuditLog(
            admin_user_id=admin_user_id,
            request_id=request_id,
            action=action,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
        )
    )


async def _get_donor_profile(db: AsyncSession, user_id: int) -> DonorProfile | None:
    row = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    return row.scalar_one_or_none()


def _donor_verification_status_from_preferences(prof: DonorProfile | None) -> str:
    if not prof or not prof.preferences:
        return "REGISTERED"
    status = (prof.preferences.get("verification_status") or "REGISTERED").upper()
    return status


async def _get_profile_status(db: AsyncSession, user_id: int, request_type: str) -> str:
    if request_type == "DONOR":
        prof = await _get_donor_profile(db, user_id)
        stored = _donor_verification_status_from_preferences(prof)
        if stored != "REGISTERED":
            return stored
        result = await db.execute(
            select(VerificationRequest)
            .where(
                VerificationRequest.user_id == user_id,
                VerificationRequest.request_type == "DONOR",
            )
            .order_by(VerificationRequest.request_id.desc())
            .limit(1)
        )
        req = result.scalar_one_or_none()
        if not req:
            return "REGISTERED"
        if req.status == "VERIFIED":
            return "VERIFIED"
        if req.status == "REJECTED":
            return "REJECTED"
        if req.status in SUBMITTED_STATUSES or req.status == "MORE_DOCUMENTS_REQUIRED":
            return "UNDER_REVIEW"
        if req.status in EDITABLE_STATUSES:
            return "KYC_IN_PROGRESS"
        return stored
    if request_type == "NGO":
        row = await db.execute(select(NgoProfile).where(NgoProfile.user_id == user_id))
        prof = row.scalar_one_or_none()
        return (prof.verification_status or "REGISTERED").upper() if prof else "REGISTERED"
    if request_type == "RECEIVER":
        row = await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == user_id))
        prof = row.scalar_one_or_none()
        return (prof.verification_status or "REGISTERED").upper() if prof else "REGISTERED"
    return "REGISTERED"


async def _set_profile_status(
    db: AsyncSession, user_id: int, request_type: str, status: str
) -> None:
    status = status.upper()
    if request_type == "DONOR":
        prof = await _get_donor_profile(db, user_id)
        if prof:
            prefs = dict(prof.preferences or {})
            prefs["verification_status"] = status
            prof.preferences = prefs
        return
    if request_type == "NGO":
        row = await db.execute(select(NgoProfile).where(NgoProfile.user_id == user_id))
        prof = row.scalar_one_or_none()
        if prof:
            prof.verification_status = status
    elif request_type == "RECEIVER":
        row = await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == user_id))
        prof = row.scalar_one_or_none()
        if prof:
            prof.verification_status = status


def _mask_sensitive_in_response(req: VerificationRequest) -> bool:
    """Receivers editing a draft need full values in API responses."""
    if req.request_type != "RECEIVER":
        return True
    editable = req.status in EDITABLE_STATUSES | {
        "DRAFT",
        "REJECTED",
        "MORE_DOCUMENTS_REQUIRED",
        "KYC_IN_PROGRESS",
    }
    return not editable


def _serialize_request(req: VerificationRequest, *, mask_sensitive: bool | None = None) -> dict[str, Any]:
    if mask_sensitive is None:
        mask_sensitive = _mask_sensitive_in_response(req)
    reasons = [r.reason for r in (req.rejection_reasons or [])]
    payload = req.payload or {}
    if mask_sensitive and req.request_type == "RECEIVER":
        payload = mask_payload_sensitive(payload)
    return {
        "request_id": req.request_id,
        "reference_code": req.reference_code,
        "user_id": req.user_id,
        "request_type": req.request_type,
        "status": req.status,
        "submitted_at": req.submitted_at,
        "reviewed_at": req.reviewed_at,
        "risk_level": req.risk_level,
        "risk_flags": req.risk_flags or [],
        "consent_given": bool(req.consent_given),
        "consent_version": req.consent_version,
        "consent_timestamp": req.consent_timestamp,
        "payload": payload,
        "current_step": int(req.current_step or 1),
        "documents": [
            {
                "document_id": d.document_id,
                "document_type": d.document_type,
                "original_filename": d.original_filename,
                "mime_type": d.mime_type,
                "size_bytes": d.size_bytes,
                "verification_status": d.verification_status,
                "uploaded_at": d.uploaded_at,
                "rejection_reason": d.rejection_reason,
            }
            for d in (req.documents or [])
        ],
        "history": [
            {
                "history_id": h.history_id,
                "status": h.status,
                "note": h.note,
                "changed_at": h.changed_at,
                "changed_by": h.changed_by,
            }
            for h in sorted(req.history or [], key=lambda x: x.changed_at or _now())
        ],
        "rejection_reasons": reasons,
    }


async def _load_request(
    db: AsyncSession, request_id: int, *, user_id: int | None = None
) -> VerificationRequest:
    stmt = (
        select(VerificationRequest)
        .where(VerificationRequest.request_id == request_id)
        .options(
            selectinload(VerificationRequest.documents),
            selectinload(VerificationRequest.history),
            selectinload(VerificationRequest.rejection_reasons),
        )
    )
    if user_id is not None:
        stmt = stmt.where(VerificationRequest.user_id == user_id)
    result = await db.execute(stmt)
    req = result.scalar_one_or_none()
    if not req:
        raise LookupError("Verification request not found")
    return req


async def get_my_verification(db: AsyncSession, user_id: int, role: str) -> dict[str, Any]:
    request_type = ROLE_TO_REQUEST_TYPE.get(role.upper())
    if not request_type:
        raise PermissionError("Invalid role for verification")
    profile_status = await _get_profile_status(db, user_id, request_type)
    result = await db.execute(
        select(VerificationRequest)
        .where(
            VerificationRequest.user_id == user_id,
            VerificationRequest.request_type == request_type,
        )
        .order_by(VerificationRequest.request_id.desc())
        .limit(1)
        .options(
            selectinload(VerificationRequest.documents),
            selectinload(VerificationRequest.history),
            selectinload(VerificationRequest.rejection_reasons),
        )
    )
    req = result.scalar_one_or_none()
    return {
        "profile_status": profile_status,
        "request": _serialize_request(req) if req else None,
    }


async def get_or_create_draft(
    db: AsyncSession, user_id: int, role: str
) -> dict[str, Any]:
    request_type = ROLE_TO_REQUEST_TYPE.get(role.upper())
    if not request_type:
        raise PermissionError("Invalid role for verification")

    result = await db.execute(
        select(VerificationRequest)
        .where(
            VerificationRequest.user_id == user_id,
            VerificationRequest.request_type == request_type,
        )
        .order_by(VerificationRequest.request_id.desc())
        .limit(1)
        .options(
            selectinload(VerificationRequest.documents),
            selectinload(VerificationRequest.history),
            selectinload(VerificationRequest.rejection_reasons),
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.status in TERMINAL_REQUEST_STATUSES | SUBMITTED_STATUSES:
            return _serialize_request(existing)
        if existing.status in EDITABLE_STATUSES:
            return _serialize_request(existing)

    req = VerificationRequest(
        user_id=user_id,
        request_type=request_type,
        status="DRAFT",
        payload={},
        current_step=1,
    )
    db.add(req)
    await db.flush()
    req.reference_code = _reference_code(req.request_id)
    await _record_history(db, req.request_id, "DRAFT", note="KYC started")
    profile_status = "KYC_IN_PROGRESS" if request_type in {"RECEIVER", "DONOR"} else "REGISTERED"
    await _set_profile_status(db, user_id, request_type, profile_status)
    await db.commit()
    await db.refresh(req)
    req = await _load_request(db, req.request_id)
    return _serialize_request(req)


async def update_draft(
    db: AsyncSession,
    user_id: int,
    request_id: int,
    *,
    payload: dict[str, Any] | None = None,
    current_step: int | None = None,
) -> dict[str, Any]:
    req = await _load_request(db, request_id, user_id=user_id)
    if req.status not in EDITABLE_STATUSES | {"DRAFT", "REJECTED", "MORE_DOCUMENTS_REQUIRED", "KYC_IN_PROGRESS"}:
        raise PermissionError("This verification request cannot be edited")
    if payload is not None:
        merged = dict(req.payload or {})
        for section_key, section_val in payload.items():
            if not isinstance(section_val, dict):
                merged[section_key] = section_val
                continue
            existing_section = dict(merged.get(section_key) or {})
            for field_key, field_val in section_val.items():
                if section_key == "identity" and field_key == "id_number" and looks_masked_value(field_val):
                    continue
                if section_key == "bank" and field_key == "account_number" and looks_masked_value(field_val):
                    continue
                existing_section[field_key] = field_val
            merged[section_key] = existing_section
        req.payload = merged
    if current_step is not None:
        req.current_step = max(1, int(current_step))
    req.updated_at = _now()
    await db.commit()
    req = await _load_request(db, request_id, user_id=user_id)
    return _serialize_request(req)


async def upload_document(
    db: AsyncSession,
    user_id: int,
    request_id: int,
    *,
    document_type: str,
    file: UploadFile,
) -> dict[str, Any]:
    req = await _load_request(db, request_id, user_id=user_id)
    if req.status not in EDITABLE_STATUSES | {"DRAFT", "REJECTED", "MORE_DOCUMENTS_REQUIRED", "KYC_IN_PROGRESS"}:
        raise PermissionError("Cannot upload documents for this request status")

    if req.request_type == "DONOR" and document_type not in DONOR_ALLOWED_DOCUMENT_TYPES:
        raise ValueError(f"Document type {document_type} is not allowed for donor verification")

    existing = await db.execute(
        select(VerificationDocument).where(
            VerificationDocument.request_id == request_id,
            VerificationDocument.document_type == document_type,
        )
    )
    for doc in existing.scalars().all():
        delete_storage_file(doc.storage_key or doc.file_url)
        await db.delete(doc)

    storage_key, original, mime, size = await save_kyc_document(
        user_id=user_id, request_id=request_id, file=file
    )
    doc = VerificationDocument(
        request_id=request_id,
        document_type=document_type,
        storage_key=storage_key,
        file_url="",
        original_filename=original,
        mime_type=mime,
        size_bytes=size,
        verification_status="UPLOADED",
        verification_source="MANUAL",
        metadata_json={"validation": "MANUAL_REVIEW_REQUIRED"},
    )
    db.add(doc)
    await db.commit()
    req = await _load_request(db, request_id, user_id=user_id)
    return _serialize_request(req)


async def delete_document(
    db: AsyncSession, user_id: int, request_id: int, document_id: int
) -> dict[str, Any]:
    req = await _load_request(db, request_id, user_id=user_id)
    if req.status not in EDITABLE_STATUSES | {"DRAFT", "REJECTED", "MORE_DOCUMENTS_REQUIRED", "KYC_IN_PROGRESS"}:
        raise PermissionError("Cannot delete documents for this request status")
    result = await db.execute(
        select(VerificationDocument).where(
            VerificationDocument.document_id == document_id,
            VerificationDocument.request_id == request_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise LookupError("Document not found")
    delete_storage_file(doc.storage_key or doc.file_url)
    await db.delete(doc)
    await db.commit()
    req = await _load_request(db, request_id, user_id=user_id)
    return _serialize_request(req)


async def get_kyc_readiness(
    db: AsyncSession,
    user_id: int,
    request_id: int,
    *,
    consent_given: bool = False,
) -> dict[str, Any]:
    req = await _load_request(db, request_id, user_id=user_id)
    uploaded = [d.document_type for d in (req.documents or [])]
    if req.request_type == "DONOR":
        return build_donor_readiness_response(uploaded_document_types=uploaded)
    return build_kyc_readiness_response(
        payload=req.payload,
        uploaded_document_types=uploaded,
        consent_given=consent_given,
    )


async def submit_verification(
    db: AsyncSession,
    user_id: int,
    request_id: int,
    *,
    consent_given: bool,
    consent_version: str,
) -> dict[str, Any]:
    req = await _load_request(db, request_id, user_id=user_id)
    if req.status in SUBMITTED_STATUSES:
        return _serialize_request(req)
    if req.status not in EDITABLE_STATUSES | {"DRAFT", "REJECTED", "MORE_DOCUMENTS_REQUIRED", "KYC_IN_PROGRESS"}:
        raise PermissionError("This verification request cannot be submitted")

    uploaded = [d.document_type for d in (req.documents or [])]
    if req.request_type == "RECEIVER":
        errors = validate_receiver_kyc_submission(
            payload=req.payload,
            uploaded_document_types=uploaded,
            consent_given=consent_given,
        )
        if errors:
            raise KycValidationError(errors)
    elif req.request_type == "DONOR":
        errors = validate_donor_verification_submission(uploaded_document_types=uploaded)
        if errors:
            raise KycValidationError(errors)
    elif not consent_given:
        raise ValueError("Consent is required before submission")

    payload = dict(req.payload or {})
    for key in ("admin_document_requests", "admin_field_requests"):
        items = list(payload.get(key) or [])
        for item in items:
            if item.get("status") in (None, "PENDING", "MORE_INFORMATION_REQUIRED"):
                item["status"] = "RESUBMITTED"
        payload[key] = items
    req.payload = payload

    req.consent_given = True
    req.consent_version = consent_version
    req.consent_timestamp = _now()
    req.submitted_at = _now()
    req.status = "DOCUMENTS_SUBMITTED"
    await _record_history(db, request_id, "DOCUMENTS_SUBMITTED", changed_by=user_id)
    req.status = "VALIDATION_IN_PROGRESS"
    await _record_history(db, request_id, "VALIDATION_IN_PROGRESS", note="Running checks")

    if req.request_type == "RECEIVER" and req.payload:
        req.payload = await _apply_identity_verification(req.payload)

    if req.request_type == "RECEIVER":
        flags, level = await evaluate_receiver_risk(db, user_id=user_id, payload=req.payload)
    elif req.request_type == "DONOR":
        flags, level = ["MANUAL_REVIEW_REQUIRED"], "LOW"
    else:
        flags, level = _ngo_risk_flags(req.payload)

    req.risk_flags = flags
    req.risk_level = level
    req.status = "UNDER_REVIEW"
    await _record_history(db, request_id, "UNDER_REVIEW", note="Queued for admin review")
    await _set_profile_status(db, user_id, req.request_type, "UNDER_REVIEW")
    await db.commit()

    admin_action_url = (
        admin_kyc_review_url(request_id=int(request_id), request_type=req.request_type)
        if req.request_type in {"NGO", "RECEIVER", "DONOR"}
        else admin_item_verification_url()
    )
    user_action = {
        "NGO": "/dashboard/ngo-verify",
        "DONOR": "/dashboard/donor-verify",
    }.get(req.request_type, "/dashboard/receiver-verify")
    event_submitted = {
        "NGO": "NGO_VERIFICATION_SUBMITTED",
        "DONOR": "DONOR_VERIFICATION_SUBMITTED",
    }.get(req.request_type, "PROFILE_VERIFICATION_SUBMITTED")
    try:
        await notify_user(
            user_id=int(user_id),
            title="Verification submitted",
            message="Your documents have been submitted and are under admin review.",
            notification_type="ACCOUNT",
            event_type=event_submitted,
            related_entity_type="VERIFICATION",
            related_entity_id=int(request_id),
            action_url=user_action,
            idempotency_key=f"kyc-submitted:{request_id}",
        )
        await notify_user(
            user_id=settings.ADMIN_NOTIFY_USER_ID,
            title=f"New {req.request_type} verification",
            message=f"Verification {req.reference_code} is ready for review.",
            notification_type="ACCOUNT",
            related_entity_type="VERIFICATION",
            related_entity_id=int(request_id),
            action_url=admin_action_url,
        )
    except Exception:
        logger.warning(
            "KYC submit notifications failed for request_id=%s (submission already saved)",
            request_id,
            exc_info=True,
        )

    req = await _load_request(db, request_id, user_id=user_id)
    return _serialize_request(req)


async def get_document_for_download(
    db: AsyncSession,
    *,
    request_id: int,
    document_id: int,
    user_id: int | None,
    is_admin: bool,
) -> tuple[VerificationDocument, VerificationRequest]:
    req = await _load_request(db, request_id, user_id=None if is_admin else user_id)
    if not is_admin and req.user_id != user_id:
        raise PermissionError("Access denied")
    result = await db.execute(
        select(VerificationDocument).where(
            VerificationDocument.document_id == document_id,
            VerificationDocument.request_id == request_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise LookupError("Document not found")
    return doc, req


async def list_admin_queue(
    db: AsyncSession,
    *,
    request_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    stmt = select(VerificationRequest).order_by(VerificationRequest.submitted_at.desc().nullslast())
    if request_type:
        stmt = stmt.where(VerificationRequest.request_type == request_type.upper())
    if status:
        stmt = stmt.where(VerificationRequest.status == status.upper())
    else:
        stmt = stmt.where(
            VerificationRequest.status.in_([
                "DOCUMENTS_SUBMITTED",
                "UNDER_REVIEW",
                "VALIDATION_IN_PROGRESS",
                "MORE_DOCUMENTS_REQUIRED",
                "REJECTED",
                "VERIFIED",
                "SUSPENDED",
            ])
        )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    items: list[dict[str, Any]] = []
    for req in rows:
        name = None
        email = None
        mobile = None
        if req.request_type == "NGO":
            prof = (
                await db.execute(select(NgoProfile).where(NgoProfile.user_id == req.user_id))
            ).scalar_one_or_none()
            if prof:
                name = prof.ngo_name
                mobile = prof.mobile
        elif req.request_type == "DONOR":
            prof = (
                await db.execute(select(DonorProfile).where(DonorProfile.user_id == req.user_id))
            ).scalar_one_or_none()
            if prof:
                name = prof.full_name
                email = prof.email
                mobile = prof.mobile
        elif req.request_type == "RECEIVER":
            prof = (
                await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == req.user_id))
            ).scalar_one_or_none()
            if prof:
                name = prof.full_name
                email = prof.email
                mobile = prof.mobile
        items.append(
            {
                "request_id": req.request_id,
                "reference_code": req.reference_code,
                "user_id": req.user_id,
                "request_type": req.request_type,
                "status": req.status,
                "submitted_at": req.submitted_at,
                "updated_at": req.updated_at,
                "risk_level": req.risk_level,
                "risk_flags": req.risk_flags or [],
                "applicant_name": name,
                "applicant_email": email,
                "applicant_mobile": mobile,
            }
        )
    return items


async def get_admin_detail(db: AsyncSession, request_id: int) -> dict[str, Any]:
    req = await _load_request(db, request_id)
    data = _serialize_request(req)
    if req.request_type == "NGO":
        prof = (
            await db.execute(select(NgoProfile).where(NgoProfile.user_id == req.user_id))
        ).scalar_one_or_none()
        if prof:
            data["applicant"] = {
                "name": prof.ngo_name,
                "registration_number": prof.registration_number,
                "contact_person": prof.contact_person,
                "mobile": prof.mobile,
            }
    elif req.request_type == "RECEIVER":
        prof = (
            await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == req.user_id))
        ).scalar_one_or_none()
        if prof:
            data["applicant"] = {
                "name": prof.full_name,
                "mobile": prof.mobile,
                "email": prof.email,
            }
    elif req.request_type == "DONOR":
        prof = (
            await db.execute(select(DonorProfile).where(DonorProfile.user_id == req.user_id))
        ).scalar_one_or_none()
        if prof:
            data["applicant"] = {
                "donor_id": prof.donor_id,
                "name": prof.full_name,
                "mobile": prof.mobile,
                "email": prof.email,
                "city": prof.location_city,
                "state": prof.location_state,
                "country": prof.location_country,
            }
    data["document_specs"] = (
        build_donor_verification_config_response()["documents"]
        if req.request_type == "DONOR"
        else None
    )
    return data


async def admin_approve(
    db: AsyncSession, admin_user_id: int, request_id: int, note: str | None = None
) -> dict[str, Any]:
    req = await _load_request(db, request_id)
    old = req.status
    if old == "VERIFIED":
        return _serialize_request(req)
    req.status = "VERIFIED"
    req.reviewed_at = _now()
    req.reviewed_by = admin_user_id
    await _record_history(db, request_id, "VERIFIED", note=note or "Approved by admin", changed_by=admin_user_id)
    await _set_profile_status(db, req.user_id, req.request_type, "VERIFIED")
    await _audit(
        db,
        admin_user_id=admin_user_id,
        request_id=request_id,
        action="ADMIN_APPROVED_VERIFICATION",
        old_status=old,
        new_status="VERIFIED",
        reason=note,
    )
    await db.commit()

    action_url = {
        "NGO": "/dashboard/ngo-verify",
        "DONOR": "/dashboard/donor-verify",
    }.get(req.request_type, "/dashboard/receiver-verify")
    event_verified = {
        "NGO": "NGO_VERIFIED",
        "DONOR": "DONOR_VERIFIED",
    }.get(req.request_type, "PROFILE_VERIFIED")
    await notify_user(
        user_id=int(req.user_id),
        title="Verification approved",
        message="Your verification has been approved. Restricted features are now unlocked.",
        notification_type="ACCOUNT",
        event_type=event_verified,
        related_entity_type="VERIFICATION",
        related_entity_id=int(request_id),
        action_url=action_url,
        idempotency_key=f"kyc-verified:{request_id}",
    )
    req = await _load_request(db, request_id)
    return _serialize_request(req)


async def admin_reject(
    db: AsyncSession, admin_user_id: int, request_id: int, reason: str
) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("Rejection reason is required")
    req = await _load_request(db, request_id)
    old = req.status
    req.status = "REJECTED"
    req.reviewed_at = _now()
    req.reviewed_by = admin_user_id
    db.add(RejectionReason(request_id=request_id, reason=reason.strip()))
    await _record_history(db, request_id, "REJECTED", note=reason.strip(), changed_by=admin_user_id)
    await _set_profile_status(db, req.user_id, req.request_type, "REJECTED")
    await _audit(
        db,
        admin_user_id=admin_user_id,
        request_id=request_id,
        action="ADMIN_REJECTED_VERIFICATION",
        old_status=old,
        new_status="REJECTED",
        reason=reason.strip(),
    )
    await db.commit()

    action_url = {
        "NGO": "/dashboard/ngo-verify",
        "DONOR": "/dashboard/donor-verify",
    }.get(req.request_type, "/dashboard/receiver-verify")
    event_rejected = {
        "NGO": "NGO_REJECTED",
        "DONOR": "DONOR_REJECTED",
    }.get(req.request_type, "PROFILE_REJECTED")
    await notify_user(
        user_id=int(req.user_id),
        title="Verification needs attention",
        message=f"Your verification was not approved. {reason.strip()}",
        notification_type="ACCOUNT",
        event_type=event_rejected,
        related_entity_type="VERIFICATION",
        related_entity_id=int(request_id),
        action_url=action_url,
        template_data={"rejection_reason": reason.strip()},
        idempotency_key=f"kyc-rejected:{request_id}",
    )
    req = await _load_request(db, request_id)
    return _serialize_request(req)


async def record_mobile_verification(
    db: AsyncSession,
    user_id: int,
    request_id: int,
    *,
    mobile: str,
    verified_at: datetime,
) -> dict[str, Any]:
    req = await _load_request(db, request_id, user_id=user_id)
    payload = dict(req.payload or {})
    mobile_digits = "".join(c for c in mobile if c.isdigit())[-10:]
    payload["mobile"] = {"mobile": mobile_digits}
    payload["mobile_verification"] = {
        "mobile": mobile_digits,
        "mobile_masked": f"•••• {mobile_digits[-4:]}" if len(mobile_digits) >= 4 else mobile_digits,
        "verified_at": verified_at.isoformat(),
    }
    req.payload = payload
    await _set_profile_status(db, user_id, req.request_type, "KYC_IN_PROGRESS")
    await db.commit()
    return _serialize_request(await _load_request(db, request_id, user_id=user_id))


async def admin_request_more_documents(
    db: AsyncSession,
    admin_user_id: int,
    request_id: int,
    *,
    document_type: str,
    reason: str,
    comment: str | None = None,
    deadline: str | None = None,
) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("Reason is required")
    req = await _load_request(db, request_id)
    old = req.status
    payload = dict(req.payload or {})
    requests = list(payload.get("admin_document_requests") or [])
    requests.append({
        "document_type": document_type,
        "reason": reason.strip(),
        "comment": comment,
        "deadline": deadline,
        "status": "PENDING",
        "requested_at": _now().isoformat(),
        "requested_by": admin_user_id,
    })
    payload["admin_document_requests"] = requests
    req.payload = payload
    req.status = "MORE_DOCUMENTS_REQUIRED"
    await _record_history(
        db,
        request_id,
        "MORE_DOCUMENTS_REQUIRED",
        note=reason.strip(),
        changed_by=admin_user_id,
    )
    await _set_profile_status(db, req.user_id, req.request_type, "MORE_DOCUMENTS_REQUIRED")
    await _audit(
        db,
        admin_user_id=admin_user_id,
        request_id=request_id,
        action="ADMIN_REQUESTED_DOCUMENTS",
        old_status=old,
        new_status="MORE_DOCUMENTS_REQUIRED",
        reason=reason.strip(),
    )
    await db.commit()

    action_url = "/dashboard/receiver-verify" if req.request_type == "RECEIVER" else "/dashboard/ngo-verify"
    await notify_user(
        user_id=int(req.user_id),
        title="Additional documents required",
        message=f"Please upload: {document_type.replace('_', ' ')}. {reason.strip()}",
        notification_type="ACCOUNT",
        event_type="PROFILE_MORE_DOCUMENTS_REQUIRED",
        related_entity_type="VERIFICATION",
        related_entity_id=int(request_id),
        action_url=action_url,
        idempotency_key=f"kyc-more-docs:{request_id}:{len(requests)}",
    )
    return _serialize_request(await _load_request(db, request_id))


async def admin_request_field_updates(
    db: AsyncSession,
    admin_user_id: int,
    request_id: int,
    *,
    field_paths: list[str],
    reason: str,
    comment: str | None = None,
) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("Reason is required")
    cleaned_paths = []
    for path in field_paths:
        p = str(path).strip()
        if p and p not in cleaned_paths:
            cleaned_paths.append(p)
    if not cleaned_paths:
        raise ValueError("At least one field must be selected")

    req = await _load_request(db, request_id)
    old = req.status
    payload = dict(req.payload or {})
    requests = list(payload.get("admin_field_requests") or [])
    requests.append({
        "field_paths": cleaned_paths,
        "reason": reason.strip(),
        "comment": comment,
        "status": "PENDING",
        "requested_at": _now().isoformat(),
        "requested_by": admin_user_id,
    })
    payload["admin_field_requests"] = requests
    req.payload = payload
    req.status = "MORE_DOCUMENTS_REQUIRED"
    field_labels = ", ".join(p.replace(".", " — ").replace("_", " ") for p in cleaned_paths)
    await _record_history(
        db,
        request_id,
        "MORE_DOCUMENTS_REQUIRED",
        note=f"Field updates requested: {field_labels}. {reason.strip()}",
        changed_by=admin_user_id,
    )
    await _set_profile_status(db, req.user_id, req.request_type, "MORE_DOCUMENTS_REQUIRED")
    await _audit(
        db,
        admin_user_id=admin_user_id,
        request_id=request_id,
        action="ADMIN_REQUESTED_FIELD_UPDATES",
        old_status=old,
        new_status="MORE_DOCUMENTS_REQUIRED",
        reason=reason.strip(),
    )
    await db.commit()

    action_url = "/dashboard/receiver-verify" if req.request_type == "RECEIVER" else "/dashboard/ngo-verify"
    await notify_user(
        user_id=int(req.user_id),
        title="Verification updates required",
        message=f"Please update: {field_labels}. {reason.strip()}",
        notification_type="ACCOUNT",
        event_type="PROFILE_MORE_DOCUMENTS_REQUIRED",
        related_entity_type="VERIFICATION",
        related_entity_id=int(request_id),
        action_url=action_url,
        idempotency_key=f"kyc-field-updates:{request_id}:{len(requests)}",
    )
    return _serialize_request(await _load_request(db, request_id))


async def admin_suspend(
    db: AsyncSession,
    admin_user_id: int,
    request_id: int,
    *,
    reason: str,
) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("Suspension reason is required")
    req = await _load_request(db, request_id)
    old = req.status
    req.status = "SUSPENDED"
    req.reviewed_at = _now()
    req.reviewed_by = admin_user_id
    await _record_history(db, request_id, "SUSPENDED", note=reason.strip(), changed_by=admin_user_id)
    await _set_profile_status(db, req.user_id, req.request_type, "SUSPENDED")
    await _audit(
        db,
        admin_user_id=admin_user_id,
        request_id=request_id,
        action="ADMIN_SUSPENDED_VERIFICATION",
        old_status=old,
        new_status="SUSPENDED",
        reason=reason.strip(),
    )
    await db.commit()

    action_url = "/dashboard/receiver-verify" if req.request_type == "RECEIVER" else "/dashboard/ngo-verify"
    await notify_user(
        user_id=int(req.user_id),
        title="Account verification suspended",
        message=reason.strip(),
        notification_type="ACCOUNT",
        event_type="PROFILE_SUSPENDED",
        related_entity_type="VERIFICATION",
        related_entity_id=int(request_id),
        action_url=action_url,
        idempotency_key=f"kyc-suspended:{request_id}",
    )
    return _serialize_request(await _load_request(db, request_id))
