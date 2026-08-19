from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.schemas.verification import (
    AdminApproveRequest,
    AdminRejectRequest,
    AdminRequestDocumentsBody,
    AdminRequestFieldUpdatesBody,
    AdminSuspendRequest,
    AdminVerificationListItem,
    VerificationRequestOut,
)
from core_app.services import verification_service as service

router = APIRouter(prefix="/admin/verifications", tags=["Admin KYC Verification"])


@router.get("", response_model=list[AdminVerificationListItem])
async def list_verifications(
    request_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    return await service.list_admin_queue(db, request_type=request_type, status=status)


@router.get("/{request_id}")
async def get_verification_detail(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.get_admin_detail(db, request_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{request_id}/approve", response_model=VerificationRequestOut)
async def approve_verification(
    request_id: int,
    body: AdminApproveRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.admin_approve(db, user.user_id, request_id, body.note)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{request_id}/reject", response_model=VerificationRequestOut)
async def reject_verification(
    request_id: int,
    body: AdminRejectRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.admin_reject(db, user.user_id, request_id, body.reason)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{request_id}/request-documents", response_model=VerificationRequestOut)
async def request_more_documents(
    request_id: int,
    body: AdminRequestDocumentsBody,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.admin_request_more_documents(
            db,
            user.user_id,
            request_id,
            document_type=body.document_type,
            reason=body.reason,
            comment=body.comment,
            deadline=body.deadline,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{request_id}/request-field-updates", response_model=VerificationRequestOut)
async def request_field_updates(
    request_id: int,
    body: AdminRequestFieldUpdatesBody,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.admin_request_field_updates(
            db,
            user.user_id,
            request_id,
            field_paths=body.field_paths,
            reason=body.reason,
            comment=body.comment,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{request_id}/suspend", response_model=VerificationRequestOut)
async def suspend_verification(
    request_id: int,
    body: AdminSuspendRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.admin_suspend(db, user.user_id, request_id, reason=body.reason)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
