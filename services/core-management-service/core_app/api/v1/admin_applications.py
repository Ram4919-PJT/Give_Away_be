from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.schemas.assistance_application import AssistanceApplicationOut, AssistanceDisburseRequest, AssistanceReviewRequest
from core_app.services import assistance_application_service as service

router = APIRouter(prefix="/admin/applications", tags=["Admin Assistance Review"])


@router.get("/queue", response_model=list[AssistanceApplicationOut])
async def get_assistance_review_queue(
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    return await service.list_admin_queue(db, status=status)


@router.get("/{application_id}", response_model=AssistanceApplicationOut)
async def get_admin_application_detail(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.get_admin_detail(db, application_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{application_id}/review", response_model=AssistanceApplicationOut)
async def review_assistance_application(
    application_id: int,
    data: AssistanceReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.review_application(
            db,
            admin_user_id=user.user_id,
            application_id=application_id,
            action=data.action,
            approved_amount=data.approved_amount,
            rejection_reason=data.rejection_reason,
            action_required_reason=data.action_required_reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{application_id}/disburse", response_model=AssistanceApplicationOut)
async def disburse_assistance_application(
    application_id: int,
    data: AssistanceDisburseRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.disburse_application(
            db,
            admin_user_id=user.user_id,
            application_id=application_id,
            disbursement_reference=data.disbursement_reference,
            note=data.note,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
