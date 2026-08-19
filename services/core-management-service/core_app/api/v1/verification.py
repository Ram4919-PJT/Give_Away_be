from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.exceptions import KycValidationError
from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user, require_roles
from core_app.schemas.verification import (
    KycReadinessResponse,
    MobileOtpSendRequest,
    MobileOtpSendResponse,
    MobileOtpVerifyRequest,
    ReceiverEligibilityResponse,
    VerificationDraftUpdate,
    VerificationMeResponse,
    VerificationRequestOut,
    VerificationSubmitRequest,
)
from core_app.services import verification_service as service
from core_app.services.kyc_mobile_otp_service import send_mobile_otp, verify_mobile_otp
from core_app.services.receiver_eligibility_service import can_receiver_request_money
from core_app.services.kyc_document_storage import resolve_storage_path

router = APIRouter(prefix="/verification", tags=["Verification"])


def _role_for_user(user: TokenUser) -> str:
    role = (user.role or "").upper()
    if role not in service.ROLE_TO_REQUEST_TYPE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot access KYC")
    return role


@router.get("/me", response_model=VerificationMeResponse)
async def get_my_verification(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    try:
        data = await service.get_my_verification(db, user.user_id, _role_for_user(user))
        return data
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/eligibility", response_model=ReceiverEligibilityResponse)
async def get_receiver_eligibility(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    role = (user.role or "").upper()
    if role != "RECEIVER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Receiver only")
    return await can_receiver_request_money(db, user.user_id)


@router.post("/mobile/send-otp", response_model=MobileOtpSendResponse)
async def send_kyc_mobile_otp(
    body: MobileOtpSendRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    if (user.role or "").upper() != "RECEIVER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Receiver only")
    try:
        issued, dev_otp = await send_mobile_otp(db, user_id=user.user_id, mobile=body.mobile)
        if issued:
            return MobileOtpSendResponse(
                sent=True,
                message="OTP sent successfully. Check your SMS.",
                dev_otp=dev_otp,
            )
        return MobileOtpSendResponse(
            sent=False,
            message="An OTP was already sent recently. Enter that code or wait before resending.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/mobile/verify-otp", response_model=VerificationRequestOut)
async def verify_kyc_mobile_otp(
    body: MobileOtpVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    if (user.role or "").upper() != "RECEIVER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Receiver only")
    try:
        verified_at = await verify_mobile_otp(
            db, user_id=user.user_id, mobile=body.mobile, otp_code=body.otp_code
        )
        return await service.record_mobile_verification(
            db,
            user.user_id,
            body.request_id,
            mobile=body.mobile,
            verified_at=verified_at,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/requests", response_model=VerificationRequestOut, status_code=status.HTTP_201_CREATED)
async def create_or_resume_verification(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    try:
        return await service.get_or_create_draft(db, user.user_id, _role_for_user(user))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/requests/{request_id}", response_model=VerificationRequestOut)
async def update_verification_draft(
    request_id: int,
    body: VerificationDraftUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    try:
        return await service.update_draft(
            db,
            user.user_id,
            request_id,
            payload=body.payload,
            current_step=body.current_step,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/requests/{request_id}/documents", response_model=VerificationRequestOut)
async def upload_verification_document(
    request_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    try:
        return await service.upload_document(
            db,
            user.user_id,
            request_id,
            document_type=document_type,
            file=file,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/requests/{request_id}/documents/{document_id}", response_model=VerificationRequestOut)
async def delete_verification_document(
    request_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    try:
        return await service.delete_document(db, user.user_id, request_id, document_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/requests/{request_id}/readiness", response_model=KycReadinessResponse)
async def get_verification_readiness(
    request_id: int,
    consent_given: bool = False,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    try:
        return await service.get_kyc_readiness(
            db,
            user.user_id,
            request_id,
            consent_given=consent_given,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/requests/{request_id}/submit", response_model=VerificationRequestOut)
async def submit_verification_request(
    request_id: int,
    body: VerificationSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    try:
        return await service.submit_verification(
            db,
            user.user_id,
            request_id,
            consent_given=body.consent_given,
            consent_version=body.consent_version,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except KycValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.errors,
        ) from exc


@router.get("/requests/{request_id}/documents/{document_id}/view")
async def view_verification_document(
    request_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    is_admin = (user.role or "").upper() == "SUPER_ADMIN"
    try:
        doc, _req = await service.get_document_for_download(
            db,
            request_id=request_id,
            document_id=document_id,
            user_id=user.user_id,
            is_admin=is_admin,
        )
        path = resolve_storage_path(doc.storage_key or doc.file_url)
        return FileResponse(
            path,
            media_type=doc.mime_type or "application/octet-stream",
            filename=doc.original_filename or "document",
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document unavailable") from exc


# Legacy admin review endpoint (backward compatible)
from pydantic import BaseModel


class LegacyReviewRequest(BaseModel):
    status: str
    reason: str | None = None


@router.post("/requests/{request_id}/review")
async def legacy_review_verification(
    request_id: int,
    action: LegacyReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    new_status = action.status.upper()
    try:
        if new_status == "VERIFIED":
            return await service.admin_approve(db, user.user_id, request_id, action.reason)
        if new_status == "REJECTED":
            return await service.admin_reject(db, user.user_id, request_id, action.reason or "")
        raise HTTPException(status_code=400, detail="Unsupported status")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
