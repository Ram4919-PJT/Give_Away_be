from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.schemas.item_donation import (
    CatalogItemDetailOut,
    CatalogListResponse,
    ItemDonationReviewRequest,
    ItemDonationOut,
)
from core_app.services import item_donation_service as service

router = APIRouter(prefix="/admin/item-donations", tags=["Admin Item Verification"])


@router.get("/queue", response_model=list[ItemDonationOut])
async def get_item_verification_queue(
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    return await service.list_verification_queue(db, status=status)


@router.get("/{item_donation_id}", response_model=ItemDonationOut)
async def get_admin_item_detail(
    item_donation_id: int,
    db: AsyncSession = Depends(get_db),
    _user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.get_admin_item_detail(db, item_donation_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{item_donation_id}/review", response_model=ItemDonationOut)
async def review_item_donation(
    item_donation_id: int,
    data: ItemDonationReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("SUPER_ADMIN")),
):
    try:
        return await service.review_item_donation(
            db,
            admin_user_id=user.user_id,
            item_donation_id=item_donation_id,
            action=data.action,
            rejection_reason=data.rejection_reason,
            change_comment=data.change_comment,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
