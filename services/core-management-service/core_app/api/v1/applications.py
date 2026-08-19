from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.exceptions import AssistanceValidationError
from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user, require_roles
from core_app.dependencies.ngo_auth import require_verified_ngo_profile
from core_app.models.applications import NgoFundRequest, NgoItemRequest
from core_app.models.profiles import NgoProfile
from core_app.schemas.assistance_application import (
    AssistanceApplicationCreate,
    AssistanceApplicationOut,
    AssistanceApplicationUpdate,
    AssistanceReadinessResponse,
    BankDetailsSubmit,
)
from core_app.services import assistance_application_service as assistance_service
from core_app.services.assistance_document_storage import resolve_assistance_storage_path
from core_app.services.ngo_service import is_ngo_suspended, is_ngo_verified, require_ngo_profile
from core_app.dependencies.ngo_auth import SUSPENDED_DETAIL, VERIFIED_ONLY_DETAIL

router = APIRouter(prefix="/applications", tags=["Assistance Applications"])


class NgoItemRequestCreate(BaseModel):
    ngo_id: int
    item_category: str
    quantity_requested: int


class NgoFundRequestCreate(BaseModel):
    ngo_id: int
    amount_requested: float
    purpose: str


class ReviewAppRequest(BaseModel):
    status: str


@router.get("", response_model=list[AssistanceApplicationOut])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    if user.role == "SUPER_ADMIN":
        return await assistance_service.list_all_applications(db)
    if user.role == "RECEIVER":
        return await assistance_service.list_receiver_applications(db, user.user_id)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.post("", response_model=AssistanceApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(
    data: AssistanceApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await assistance_service.create_receiver_application(
            db,
            user.user_id,
            purpose=data.purpose,
            amount_requested=data.amount_requested,
            category=data.category,
            expense_breakdown=data.expense_breakdown,
            notes=data.notes,
        )
    except AssistanceValidationError:
        raise
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{application_id}/readiness", response_model=AssistanceReadinessResponse)
async def get_application_readiness(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await assistance_service.get_application_readiness(db, user.user_id, application_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/{application_id}", response_model=AssistanceApplicationOut)
async def update_application(
    application_id: int,
    data: AssistanceApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await assistance_service.update_receiver_application(
            db,
            user.user_id,
            application_id,
            purpose=data.purpose,
            amount_requested=data.amount_requested,
            category=data.category,
            expense_breakdown=data.expense_breakdown,
            notes=data.notes,
        )
    except AssistanceValidationError:
        raise
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{application_id}/submit", response_model=AssistanceApplicationOut)
async def submit_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await assistance_service.submit_receiver_application(db, user.user_id, application_id)
    except AssistanceValidationError:
        raise
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{application_id}/documents", response_model=AssistanceApplicationOut)
async def upload_application_document(
    application_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await assistance_service.upload_application_document(
            db,
            user.user_id,
            application_id,
            document_type=document_type,
            file=file,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{application_id}/documents/{document_id}", response_model=AssistanceApplicationOut)
async def delete_application_document(
    application_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await assistance_service.delete_application_document(
            db, user.user_id, application_id, document_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{application_id}/documents/{document_id}/view")
async def view_application_document(
    application_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    is_admin = (user.role or "").upper() == "SUPER_ADMIN"
    try:
        doc, _app = await assistance_service.get_application_document_for_download(
            db,
            application_id=application_id,
            document_id=document_id,
            user_id=user.user_id,
            is_admin=is_admin,
        )
        path = resolve_assistance_storage_path(doc.storage_key)
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


@router.post("/{application_id}/bank-details", response_model=AssistanceApplicationOut)
async def submit_bank_details(
    application_id: int,
    data: BankDetailsSubmit,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    if data.account_number.strip() != data.confirm_account_number.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account number and confirmation do not match",
        )
    if not data.ifsc_code.strip().upper().startswith(tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enter a valid IFSC code")
    try:
        return await assistance_service.submit_bank_details(
            db,
            user.user_id,
            application_id,
            account_holder_name=data.account_holder_name,
            bank_name=data.bank_name,
            account_number=data.account_number.strip(),
            ifsc_code=data.ifsc_code.strip().upper(),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/ngo-item-requests")
async def list_ngo_item_requests(
    ngo_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    if user.role == "SUPER_ADMIN":
        stmt = select(NgoItemRequest)
        if ngo_id is not None:
            stmt = stmt.where(NgoItemRequest.ngo_id == ngo_id)
    elif user.role == "NGO":
        try:
            profile = await require_ngo_profile(db, user.user_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if is_ngo_suspended(profile):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SUSPENDED_DETAIL)
        if not is_ngo_verified(profile):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=VERIFIED_ONLY_DETAIL)
        stmt = select(NgoItemRequest).where(NgoItemRequest.ngo_id == profile.ngo_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/ngo-item-requests", status_code=status.HTTP_201_CREATED)
async def create_ngo_item_request(
    data: NgoItemRequestCreate,
    db: AsyncSession = Depends(get_db),
    profile: NgoProfile = Depends(require_verified_ngo_profile),
):
    if data.ngo_id != profile.ngo_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot submit requests for another organization.",
        )
    req = NgoItemRequest(
        ngo_id=profile.ngo_id,
        item_category=data.item_category,
        quantity_requested=data.quantity_requested,
        status="SUBMITTED",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.post("/ngo-item-requests/{request_id}/review")
async def review_ngo_item_request(
    request_id: int,
    action: ReviewAppRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    result = await db.execute(select(NgoItemRequest).where(NgoItemRequest.request_id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail=f"NGO item request #{request_id} not found")

    req.status = action.status.upper()
    await db.commit()
    return {"message": f"NGO item request #{request_id} updated to {req.status}", "status": req.status}


@router.get("/ngo-fund-requests")
async def list_ngo_fund_requests(
    ngo_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    if user.role == "SUPER_ADMIN":
        stmt = select(NgoFundRequest)
        if ngo_id is not None:
            stmt = stmt.where(NgoFundRequest.ngo_id == ngo_id)
    elif user.role == "NGO":
        try:
            profile = await require_ngo_profile(db, user.user_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if is_ngo_suspended(profile):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SUSPENDED_DETAIL)
        if not is_ngo_verified(profile):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=VERIFIED_ONLY_DETAIL)
        stmt = select(NgoFundRequest).where(NgoFundRequest.ngo_id == profile.ngo_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/ngo-fund-requests", status_code=status.HTTP_201_CREATED)
async def create_ngo_fund_request(
    data: NgoFundRequestCreate,
    db: AsyncSession = Depends(get_db),
    profile: NgoProfile = Depends(require_verified_ngo_profile),
):
    if data.ngo_id != profile.ngo_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot submit requests for another organization.",
        )
    req = NgoFundRequest(
        ngo_id=profile.ngo_id,
        amount_requested=data.amount_requested,
        purpose=data.purpose,
        status="SUBMITTED",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req


@router.post("/ngo-fund-requests/{request_id}/review")
async def review_ngo_fund_request(
    request_id: int,
    action: ReviewAppRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    result = await db.execute(select(NgoFundRequest).where(NgoFundRequest.request_id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail=f"NGO fund request #{request_id} not found")

    req.status = action.status.upper()
    await db.commit()
    return {"message": f"NGO fund request #{request_id} updated to {req.status}", "status": req.status}
