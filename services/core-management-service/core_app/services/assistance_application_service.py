from __future__ import annotations

from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core_app.config import settings
from core_app.core.exceptions import AssistanceValidationError
from core_app.integrations.notification_client import notify_user
from core_app.models.applications import (
    ApplicationStatusHistory,
    AssistanceApplication,
    AssistanceApplicationDocument,
)
from core_app.models.profiles import ReceiverProfile
from core_app.models.verification import VerificationRequest
from core_app.schemas.assistance_application import AssistanceApplicationOut
from core_app.services.assistance_document_storage import (
    delete_assistance_storage_file,
    resolve_assistance_storage_path,
    save_assistance_document,
)
from core_app.services.receiver_assistance_config import validate_assistance_category
from core_app.services.receiver_assistance_validation import (
    build_assistance_readiness_response,
    validate_assistance_application,
)
from core_app.services.receiver_eligibility_service import can_receiver_request_money
from core_app.services.receiver_kyc_payout import get_receiver_kyc_payout_info
from core_app.utils.portal_urls import admin_assistance_review_url

ADMIN_QUEUE_STATUSES = ("SUBMITTED", "UNDER_REVIEW", "PENDING_REVIEW", "OPEN", "ACTION_REQUIRED")
REVIEWABLE_STATUSES = ("SUBMITTED", "UNDER_REVIEW", "PENDING_REVIEW", "OPEN", "ACTION_REQUIRED")
EDITABLE_STATUSES = frozenset({"DRAFT", "ACTION_REQUIRED"})
DISBURSEMENT_QUEUE_PAYOUT = ("READY_FOR_DISBURSEMENT", "BANK_DETAILS_SUBMITTED", "AWAITING_BANK_DETAILS")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _loaded_relationship(instance, name: str) -> list:
    """Return relationship rows without triggering async lazy loads."""
    state = sa_inspect(instance)
    if name in state.unloaded:
        return []
    return list(state.attrs[name].value or [])


def _serialize(
    app: AssistanceApplication,
    receiver: ReceiverProfile | None = None,
    *,
    receiver_kyc_request_id: int | None = None,
    receiver_kyc_reference: str | None = None,
) -> AssistanceApplicationOut:
    docs = [
        {
            "document_id": int(d.document_id),
            "document_type": d.document_type,
            "original_filename": d.original_filename,
            "mime_type": d.mime_type,
            "size_bytes": d.size_bytes,
            "uploaded_at": d.uploaded_at,
        }
        for d in _loaded_relationship(app, "documents")
    ]
    history_rows = sorted(_loaded_relationship(app, "history"), key=lambda h: h.changed_at or _now())
    history = [
        {
            "history_id": int(h.history_id),
            "status": h.status,
            "changed_at": h.changed_at,
        }
        for h in history_rows
    ]
    return AssistanceApplicationOut(
        application_id=int(app.application_id),
        receiver_id=int(app.receiver_id),
        purpose=app.purpose,
        amount_requested=float(app.amount_requested),
        amount_approved=float(app.amount_approved) if app.amount_approved is not None else None,
        category=app.category,
        expense_breakdown=app.expense_breakdown,
        notes=app.notes,
        status=app.status,
        rejection_reason=app.rejection_reason,
        action_required_reason=app.action_required_reason,
        payout_status=app.payout_status,
        bank_account_holder=app.bank_account_holder,
        bank_name=app.bank_name,
        bank_ifsc=app.bank_ifsc,
        bank_account_last4=app.bank_account_last4,
        bank_details_submitted_at=app.bank_details_submitted_at,
        payment_destination_type=app.payment_destination_type,
        disbursement_reference=app.disbursement_reference,
        disbursed_at=app.disbursed_at,
        submitted_at=app.submitted_at,
        reviewed_at=app.reviewed_at,
        reviewed_by_user_id=int(app.reviewed_by_user_id) if app.reviewed_by_user_id else None,
        receiver_name=receiver.full_name if receiver else None,
        receiver_email=receiver.email if receiver else None,
        receiver_mobile=receiver.mobile if receiver else None,
        receiver_verification_status=receiver.verification_status if receiver else None,
        receiver_kyc_request_id=receiver_kyc_request_id,
        receiver_kyc_reference=receiver_kyc_reference,
        documents=docs,
        history=history,
    )


async def _get_receiver_profile(db: AsyncSession, user_id: int) -> ReceiverProfile:
    result = await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == user_id))
    receiver = result.scalar_one_or_none()
    if receiver is None:
        raise LookupError("Receiver profile not found for this user")
    return receiver


async def _get_receiver_by_id(db: AsyncSession, receiver_id: int) -> ReceiverProfile | None:
    result = await db.execute(select(ReceiverProfile).where(ReceiverProfile.receiver_id == receiver_id))
    return result.scalar_one_or_none()


async def _load_application(
    db: AsyncSession,
    application_id: int,
    *,
    user_id: int | None = None,
    receiver_id: int | None = None,
    is_admin: bool = False,
) -> AssistanceApplication:
    result = await db.execute(
        select(AssistanceApplication)
        .where(AssistanceApplication.application_id == application_id)
        .options(
            selectinload(AssistanceApplication.documents),
            selectinload(AssistanceApplication.history),
        )
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise LookupError("Application not found")
    if is_admin:
        return app
    if receiver_id is not None and int(app.receiver_id) != int(receiver_id):
        raise PermissionError("You do not have access to this application")
    if user_id is not None:
        receiver = await _get_receiver_profile(db, user_id)
        if int(app.receiver_id) != int(receiver.receiver_id):
            raise PermissionError("You do not have access to this application")
    return app


async def get_application_readiness(
    db: AsyncSession,
    user_id: int,
    application_id: int,
) -> dict:
    app = await _load_application(db, application_id, user_id=user_id)
    uploaded = [d.document_type for d in (app.documents or [])]
    return build_assistance_readiness_response(
        purpose=app.purpose,
        amount_requested=float(app.amount_requested),
        category=app.category,
        expense_breakdown=app.expense_breakdown,
        uploaded_document_types=uploaded,
    )


async def list_receiver_applications(db: AsyncSession, user_id: int) -> list[AssistanceApplicationOut]:
    try:
        receiver = await _get_receiver_profile(db, user_id)
    except LookupError:
        return []
    result = await db.execute(
        select(AssistanceApplication)
        .where(AssistanceApplication.receiver_id == receiver.receiver_id)
        .options(
            selectinload(AssistanceApplication.documents),
            selectinload(AssistanceApplication.history),
        )
        .order_by(AssistanceApplication.submitted_at.desc())
    )
    return [_serialize(row, receiver) for row in result.scalars().all()]


async def create_receiver_application(
    db: AsyncSession,
    user_id: int,
    *,
    purpose: str,
    amount_requested: float,
    category: str | None = None,
    expense_breakdown: str | None = None,
    notes: str | None = None,
) -> AssistanceApplicationOut:
    receiver = await _get_receiver_profile(db, user_id)
    eligibility = await can_receiver_request_money(db, user_id)
    if not eligibility["eligible"]:
        detail = "; ".join(eligibility["reasons"]) or "Receiver verification incomplete"
        raise PermissionError(detail)

    canonical_category = validate_assistance_category(category)
    uploaded: list[str] = []
    errors = validate_assistance_application(
        purpose=purpose,
        amount_requested=amount_requested,
        category=canonical_category,
        expense_breakdown=expense_breakdown,
        uploaded_document_types=uploaded,
    )
    field_errors = [e for e in errors if not e["field"].startswith("document.")]
    if field_errors:
        raise AssistanceValidationError(field_errors)

    app = AssistanceApplication(
        receiver_id=receiver.receiver_id,
        purpose=purpose.strip(),
        amount_requested=amount_requested,
        status="DRAFT",
        category=canonical_category,
        expense_breakdown=expense_breakdown,
        notes=notes,
    )

    db.add(app)
    await db.flush()
    db.add(ApplicationStatusHistory(application_id=app.application_id, status="DRAFT"))
    await db.commit()
    await db.refresh(app)
    result = await db.execute(
        select(AssistanceApplication)
        .where(AssistanceApplication.application_id == app.application_id)
        .options(selectinload(AssistanceApplication.documents))
    )
    app = result.scalar_one()
    return _serialize(app, receiver)


async def submit_receiver_application(db: AsyncSession, user_id: int, application_id: int) -> AssistanceApplicationOut:
    receiver = await _get_receiver_profile(db, user_id)
    eligibility = await can_receiver_request_money(db, user_id)
    if not eligibility["eligible"]:
        raise PermissionError(
            eligibility.get("reasons", ["Receiver KYC verification is required before requesting assistance."])[0]
        )
    app = await _load_application(db, application_id, user_id=user_id)
    if app.status not in EDITABLE_STATUSES:
        if app.status == "SUBMITTED":
            return _serialize(app, receiver)
        raise PermissionError("This application cannot be submitted in its current status")

    uploaded = [d.document_type for d in (app.documents or [])]
    errors = validate_assistance_application(
        purpose=app.purpose,
        amount_requested=float(app.amount_requested),
        category=app.category,
        expense_breakdown=app.expense_breakdown,
        uploaded_document_types=uploaded,
    )
    if errors:
        raise AssistanceValidationError(errors)

    app.status = "SUBMITTED"
    app.action_required_reason = None
    app.submitted_at = _now()
    db.add(ApplicationStatusHistory(application_id=application_id, status="SUBMITTED"))
    await db.commit()
    await db.refresh(app)

    amount_requested = float(app.amount_requested)
    await notify_user(
        user_id=int(receiver.user_id),
        title="Request submitted successfully",
        message=(
            f"Your financial assistance request for ₹{amount_requested:,.0f} "
            f"has been submitted and is pending review."
        ),
        notification_type="APPLICATION",
        event_type="FUND_REQUEST_SUBMITTED",
        related_entity_type="ASSISTANCE_APPLICATION",
        related_entity_id=int(app.application_id),
        action_url="/dashboard/receiver-requests",
        recipient_email=receiver.email,
        recipient_name=receiver.full_name,
        template_data={
            "request_id": f"APP-{app.application_id}",
            "application_id": app.application_id,
            "amount_display": f"₹{amount_requested:,.0f}",
            "status": "SUBMITTED",
        },
        idempotency_key=f"fund-request-submitted:{app.application_id}",
    )

    await notify_user(
        user_id=settings.ADMIN_NOTIFY_USER_ID,
        title="New financial assistance request",
        message=f"{receiver.full_name} submitted a request for ₹{amount_requested:,.0f}.",
        notification_type="APPLICATION",
        related_entity_type="ASSISTANCE_APPLICATION",
        related_entity_id=int(app.application_id),
        action_url=admin_assistance_review_url(application_id=int(app.application_id)),
    )

    return _serialize(app, receiver)


async def update_receiver_application(
    db: AsyncSession,
    user_id: int,
    application_id: int,
    *,
    purpose: str | None = None,
    amount_requested: float | None = None,
    category: str | None = None,
    expense_breakdown: str | None = None,
    notes: str | None = None,
) -> AssistanceApplicationOut:
    receiver = await _get_receiver_profile(db, user_id)
    app = await _load_application(db, application_id, user_id=user_id)
    if app.status not in EDITABLE_STATUSES:
        raise PermissionError("This application cannot be edited in its current status")

    if purpose is not None:
        app.purpose = purpose.strip()
    if amount_requested is not None:
        app.amount_requested = amount_requested
    if category is not None:
        app.category = validate_assistance_category(category)
    if expense_breakdown is not None:
        app.expense_breakdown = expense_breakdown
    if notes is not None:
        app.notes = notes

    uploaded = [d.document_type for d in (app.documents or [])]
    errors = validate_assistance_application(
        purpose=app.purpose,
        amount_requested=float(app.amount_requested),
        category=app.category,
        expense_breakdown=app.expense_breakdown,
        uploaded_document_types=uploaded,
    )
    field_errors = [e for e in errors if not e["field"].startswith("document.")]
    if field_errors:
        raise AssistanceValidationError(field_errors)

    await db.commit()
    await db.refresh(app)
    return _serialize(app, receiver)


async def upload_application_document(
    db: AsyncSession,
    user_id: int,
    application_id: int,
    *,
    document_type: str,
    file: UploadFile,
) -> AssistanceApplicationOut:
    receiver = await _get_receiver_profile(db, user_id)
    app = await _load_application(db, application_id, user_id=user_id)
    if app.status not in EDITABLE_STATUSES:
        raise PermissionError("Documents cannot be changed for this application")

    doc_type = document_type.strip().upper()
    if not doc_type:
        raise ValueError("document_type is required")

    existing = await db.execute(
        select(AssistanceApplicationDocument).where(
            AssistanceApplicationDocument.application_id == application_id,
            AssistanceApplicationDocument.document_type == doc_type,
        )
    )
    for old in existing.scalars().all():
        delete_assistance_storage_file(old.storage_key)
        await db.delete(old)

    storage_key, original, mime, size = await save_assistance_document(
        user_id=user_id,
        application_id=application_id,
        file=file,
    )
    doc = AssistanceApplicationDocument(
        application_id=application_id,
        document_type=doc_type,
        storage_key=storage_key,
        original_filename=original,
        mime_type=mime,
        size_bytes=size,
    )
    db.add(doc)
    await db.commit()
    app = await _load_application(db, application_id, user_id=user_id)
    return _serialize(app, receiver)


async def delete_application_document(
    db: AsyncSession,
    user_id: int,
    application_id: int,
    document_id: int,
) -> AssistanceApplicationOut:
    receiver = await _get_receiver_profile(db, user_id)
    app = await _load_application(db, application_id, user_id=user_id)
    if app.status not in EDITABLE_STATUSES:
        raise PermissionError("Documents cannot be changed for this application")

    result = await db.execute(
        select(AssistanceApplicationDocument).where(
            AssistanceApplicationDocument.document_id == document_id,
            AssistanceApplicationDocument.application_id == application_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise LookupError("Document not found")
    delete_assistance_storage_file(doc.storage_key)
    await db.delete(doc)
    await db.commit()
    app = await _load_application(db, application_id, user_id=user_id)
    return _serialize(app, receiver)


async def get_application_document_for_download(
    db: AsyncSession,
    application_id: int,
    document_id: int,
    *,
    user_id: int,
    is_admin: bool = False,
) -> tuple[AssistanceApplicationDocument, AssistanceApplication]:
    app = await _load_application(
        db,
        application_id,
        user_id=None if is_admin else user_id,
        is_admin=is_admin,
    )
    if not is_admin:
        await _load_application(db, application_id, user_id=user_id)

    result = await db.execute(
        select(AssistanceApplicationDocument).where(
            AssistanceApplicationDocument.document_id == document_id,
            AssistanceApplicationDocument.application_id == application_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise LookupError("Document not found")
    return doc, app


async def list_all_applications(db: AsyncSession) -> list[AssistanceApplicationOut]:
    result = await db.execute(
        select(AssistanceApplication)
        .options(
            selectinload(AssistanceApplication.documents),
            selectinload(AssistanceApplication.history),
        )
        .order_by(AssistanceApplication.submitted_at.desc().nullslast())
    )
    rows = result.scalars().all()
    out: list[AssistanceApplicationOut] = []
    for app in rows:
        receiver = await _get_receiver_by_id(db, int(app.receiver_id))
        out.append(_serialize(app, receiver))
    return out


async def list_admin_queue(db: AsyncSession, status: str | None = None) -> list[AssistanceApplicationOut]:
    stmt = (
        select(AssistanceApplication)
        .options(
            selectinload(AssistanceApplication.documents),
            selectinload(AssistanceApplication.history),
        )
        .order_by(AssistanceApplication.submitted_at.asc().nullslast())
    )
    if status:
        stmt = stmt.where(AssistanceApplication.status == status.upper())
    else:
        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                AssistanceApplication.status.in_(ADMIN_QUEUE_STATUSES),
                (
                    (AssistanceApplication.status == "APPROVED")
                    & AssistanceApplication.payout_status.in_(DISBURSEMENT_QUEUE_PAYOUT)
                ),
            )
        )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    out: list[AssistanceApplicationOut] = []
    for app in rows:
        receiver = await _get_receiver_by_id(db, int(app.receiver_id))
        out.append(_serialize(app, receiver))
    return out


async def _receiver_kyc_meta(
    db: AsyncSession, receiver: ReceiverProfile | None,
) -> tuple[int | None, str | None]:
    if not receiver:
        return None, None
    result = await db.execute(
        select(VerificationRequest)
        .where(
            VerificationRequest.user_id == int(receiver.user_id),
            VerificationRequest.request_type == "RECEIVER",
        )
        .order_by(VerificationRequest.request_id.desc())
        .limit(1)
    )
    req = result.scalar_one_or_none()
    if not req:
        return None, None
    return int(req.request_id), req.reference_code


async def get_admin_detail(db: AsyncSession, application_id: int) -> AssistanceApplicationOut:
    result = await db.execute(
        select(AssistanceApplication)
        .where(AssistanceApplication.application_id == application_id)
        .options(
            selectinload(AssistanceApplication.documents),
            selectinload(AssistanceApplication.history),
        )
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise LookupError("Application not found")
    receiver = await _get_receiver_by_id(db, int(app.receiver_id))
    kyc_id, kyc_ref = await _receiver_kyc_meta(db, receiver)
    return _serialize(
        app,
        receiver,
        receiver_kyc_request_id=kyc_id,
        receiver_kyc_reference=kyc_ref,
    )


async def review_application(
    db: AsyncSession,
    admin_user_id: int,
    application_id: int,
    *,
    action: str,
    approved_amount: float | None = None,
    rejection_reason: str | None = None,
    action_required_reason: str | None = None,
) -> AssistanceApplicationOut:
    result = await db.execute(
        select(AssistanceApplication)
        .where(AssistanceApplication.application_id == application_id)
        .with_for_update()
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise LookupError("Application not found")
    if app.status not in REVIEWABLE_STATUSES:
        raise ValueError("This application cannot be reviewed in its current status")

    receiver = await _get_receiver_by_id(db, int(app.receiver_id))
    if receiver is None:
        raise LookupError("Receiver profile not found")

    normalized = action.strip().lower().replace("-", "_")

    if normalized == "approve":
        verification_status = (receiver.verification_status or "").upper()
        if verification_status != "VERIFIED":
            raise PermissionError(
                "Cannot approve assistance for a receiver who is not verified. "
                "Complete KYC review first."
            )

    now = _now()
    action_url = "/dashboard/receiver-requests"

    if normalized == "approve":
        amount = approved_amount if approved_amount is not None else float(app.amount_requested)
        if amount > float(app.amount_requested):
            raise ValueError("Approved amount cannot exceed the requested amount")
        app.status = "APPROVED"
        app.amount_approved = amount
        app.reviewed_at = now
        app.reviewed_by_user_id = admin_user_id
        app.rejection_reason = None
        app.action_required_reason = None

        kyc_bank = await get_receiver_kyc_payout_info(db, int(receiver.user_id))
        if kyc_bank:
            app.bank_account_holder = kyc_bank["bank_account_holder"]
            app.bank_name = kyc_bank["bank_name"]
            app.bank_ifsc = kyc_bank["bank_ifsc"]
            app.bank_account_last4 = kyc_bank["bank_account_last4"]
            app.payment_destination_type = kyc_bank["payment_destination_type"]
            app.bank_details_submitted_at = now
            app.payout_status = "READY_FOR_DISBURSEMENT"
            message = (
                f"Your financial assistance request has been approved for ₹{amount:,.0f}. "
                f"Disbursement will be processed using your verified bank details."
            )
        else:
            app.payout_status = "AWAITING_BANK_DETAILS"
            message = (
                f"Your financial assistance request has been approved for ₹{amount:,.0f}. "
                f"Please add your bank account details to receive the funds."
            )
        title = "Financial assistance approved"
        action_url = "/dashboard/receiver-requests"
    elif normalized == "reject":
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("Rejection reason is required")
        app.status = "REJECTED"
        app.rejection_reason = rejection_reason.strip()
        app.reviewed_at = now
        app.reviewed_by_user_id = admin_user_id
        message = f"Your financial assistance request was not approved. Reason: {rejection_reason.strip()}"
        title = "Financial assistance not approved"
    elif normalized in {"under_review", "review"}:
        app.status = "UNDER_REVIEW"
        message = "Your financial assistance request is now under review."
        title = "Application under review"
    elif normalized in {"request_action", "action_required"}:
        if not action_required_reason or not action_required_reason.strip():
            raise ValueError("Action required reason is required")
        app.status = "ACTION_REQUIRED"
        app.action_required_reason = action_required_reason.strip()
        message = f"Additional information is required: {action_required_reason.strip()}"
        title = "Action required on your application"
    else:
        raise ValueError("action must be approve, reject, under_review, or request_action")

    db.add(ApplicationStatusHistory(application_id=application_id, status=app.status))
    await db.commit()
    await db.refresh(app)

    event_type = "GENERIC_NOTIFICATION"
    template_data: dict = {
        "request_id": f"APP-{app.application_id}",
        "application_id": app.application_id,
        "status": app.status,
    }
    if normalized == "approve":
        event_type = "FUND_REQUEST_APPROVED"
        template_data["amount_approved"] = f"₹{float(app.amount_approved or app.amount_requested):,.0f}"
        template_data["amount_display"] = template_data["amount_approved"]
    elif normalized == "reject":
        event_type = "FUND_REQUEST_REJECTED"
        template_data["rejection_reason"] = app.rejection_reason
        template_data["message"] = message

    await notify_user(
        user_id=int(receiver.user_id),
        title=title,
        message=message,
        notification_type="APPLICATION",
        event_type=event_type,
        related_entity_type="ASSISTANCE_APPLICATION",
        related_entity_id=int(app.application_id),
        action_url=action_url,
        recipient_email=receiver.email,
        recipient_name=receiver.full_name,
        template_data=template_data,
        idempotency_key=f"fund-request-review:{app.application_id}:{app.status}",
    )

    return _serialize(app, receiver)


async def submit_bank_details(
    db: AsyncSession,
    user_id: int,
    application_id: int,
    *,
    account_holder_name: str,
    bank_name: str,
    account_number: str,
    ifsc_code: str,
) -> AssistanceApplicationOut:
    receiver = await _get_receiver_profile(db, user_id)
    result = await db.execute(
        select(AssistanceApplication).where(
            AssistanceApplication.application_id == application_id,
            AssistanceApplication.receiver_id == receiver.receiver_id,
        )
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise LookupError("Application not found")

    if app.status != "APPROVED":
        raise PermissionError("Bank details can only be submitted for approved requests")

    if app.payout_status == "BANK_DETAILS_SUBMITTED":
        raise ValueError("Bank details have already been submitted for this request")

    if app.payout_status not in (None, "AWAITING_BANK_DETAILS"):
        raise ValueError("Bank details cannot be submitted for this request in its current state")

    clean_ifsc = ifsc_code.strip().upper()
    clean_account = account_number.strip()
    now = _now()

    app.bank_account_holder = account_holder_name.strip()
    app.bank_name = bank_name.strip()
    app.bank_ifsc = clean_ifsc
    app.bank_account_last4 = clean_account[-4:] if len(clean_account) >= 4 else clean_account
    app.payout_status = "READY_FOR_DISBURSEMENT"
    app.bank_details_submitted_at = now

    db.add(ApplicationStatusHistory(application_id=application_id, status="BANK_DETAILS_SUBMITTED"))
    await db.commit()
    await db.refresh(app)

    approved = float(app.amount_approved or app.amount_requested)
    await notify_user(
        user_id=int(receiver.user_id),
        title="Bank details received",
        message=(
            f"We received your bank details for ₹{approved:,.0f}. "
            f"Your disbursement will be processed shortly."
        ),
        notification_type="APPLICATION",
        event_type="FUND_REQUEST_FULFILLED",
        related_entity_type="DISBURSEMENT",
        related_entity_id=int(app.application_id),
        action_url="/dashboard/receiver-requests",
        recipient_email=receiver.email,
        recipient_name=receiver.full_name,
        template_data={
            "request_id": f"APP-{app.application_id}",
            "amount_display": f"₹{approved:,.0f}",
            "status": "BANK_DETAILS_SUBMITTED",
        },
        idempotency_key=f"fund-request-bank:{app.application_id}",
    )
    await notify_user(
        user_id=settings.ADMIN_NOTIFY_USER_ID,
        title="Bank details submitted",
        message=f"{receiver.full_name} submitted bank details for assistance request #{application_id}.",
        notification_type="APPLICATION",
        related_entity_type="DISBURSEMENT",
        related_entity_id=int(app.application_id),
        action_url=admin_assistance_review_url(application_id=int(app.application_id)),
    )

    return _serialize(app, receiver)


async def disburse_application(
    db: AsyncSession,
    admin_user_id: int,
    application_id: int,
    *,
    disbursement_reference: str,
    note: str | None = None,
) -> AssistanceApplicationOut:
    result = await db.execute(
        select(AssistanceApplication)
        .where(AssistanceApplication.application_id == application_id)
        .with_for_update()
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise LookupError("Application not found")
    if app.status != "APPROVED":
        raise ValueError("Only approved applications can be disbursed")
    if app.payout_status == "DISBURSED":
        receiver = await _get_receiver_by_id(db, int(app.receiver_id))
        return _serialize(app, receiver)

    allowed_payout = {"READY_FOR_DISBURSEMENT", "BANK_DETAILS_SUBMITTED"}
    if app.payout_status not in allowed_payout:
        raise ValueError(
            "Bank details must be verified before disbursement. "
            f"Current payout status: {app.payout_status}"
        )

    receiver = await _get_receiver_by_id(db, int(app.receiver_id))
    if receiver is None:
        raise LookupError("Receiver profile not found")
    if (receiver.verification_status or "").upper() != "VERIFIED":
        raise PermissionError("Receiver must remain verified to disburse funds")

    now = _now()
    app.payout_status = "DISBURSED"
    app.status = "COMPLETED"
    app.disbursement_reference = disbursement_reference.strip()
    app.disbursed_at = now
    app.disbursed_by = admin_user_id

    db.add(ApplicationStatusHistory(application_id=application_id, status="DISBURSED"))
    db.add(ApplicationStatusHistory(application_id=application_id, status="COMPLETED"))
    await db.commit()
    await db.refresh(app)

    amount = float(app.amount_approved or app.amount_requested)
    await notify_user(
        user_id=int(receiver.user_id),
        title="Assistance disbursed",
        message=(
            f"₹{amount:,.0f} has been disbursed. Reference: {app.disbursement_reference}"
        ),
        notification_type="APPLICATION",
        event_type="FUND_REQUEST_FULFILLED",
        related_entity_type="DISBURSEMENT",
        related_entity_id=int(app.application_id),
        action_url="/dashboard/receiver-requests",
        recipient_email=receiver.email,
        recipient_name=receiver.full_name,
        template_data={
            "request_id": f"APP-{app.application_id}",
            "amount_display": f"₹{amount:,.0f}",
            "disbursement_reference": app.disbursement_reference,
            "status": "DISBURSED",
            "note": note,
        },
        idempotency_key=f"fund-disbursed:{app.application_id}",
    )

    return _serialize(app, receiver)
