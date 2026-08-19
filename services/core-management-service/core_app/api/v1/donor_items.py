from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.schemas.item_donation import (
    ItemDonationCreate,
    ItemDonationOut,
    ItemDonationUpdate,
)
from core_app.services import item_donation_service as service
from core_app.services.donor_verification import DonorNotVerifiedError

router = APIRouter(prefix="/donors/me/item-donations", tags=["Donor Item Donations"])


def _handle_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, DonorNotVerifiedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise exc


@router.get("/verification-status")
async def get_my_donor_verification_status(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    from core_app.services.donor_verification import is_donor_verified

    return {"verified": await is_donor_verified(db, user.user_id)}


@router.post("", response_model=ItemDonationOut, status_code=status.HTTP_201_CREATED)
async def create_my_item_donation(
    data: ItemDonationCreate,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.create_item_donation_draft(db, user.user_id, data)
    except (LookupError, DonorNotVerifiedError, ValueError) as exc:
        raise _handle_errors(exc) from exc


@router.get("", response_model=list[ItemDonationOut])
async def list_my_item_donations(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.list_my_item_donations(db, user.user_id)
    except LookupError as exc:
        raise _handle_errors(exc) from exc


@router.get("/{item_donation_id}", response_model=ItemDonationOut)
async def get_my_item_donation(
    item_donation_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.get_owned_item_donation(db, user.user_id, item_donation_id)
    except LookupError as exc:
        raise _handle_errors(exc) from exc


@router.patch("/{item_donation_id}", response_model=ItemDonationOut)
async def update_my_item_donation(
    item_donation_id: int,
    data: ItemDonationUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.update_item_donation_draft(db, user.user_id, item_donation_id, data)
    except (LookupError, ValueError) as exc:
        raise _handle_errors(exc) from exc


@router.delete("/{item_donation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_item_donation(
    item_donation_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        await service.delete_item_donation_draft(db, user.user_id, item_donation_id)
    except (LookupError, ValueError) as exc:
        raise _handle_errors(exc) from exc


@router.post("/{item_donation_id}/documents", response_model=ItemDonationOut)
async def upload_my_item_document(
    item_donation_id: int,
    file: UploadFile = File(...),
    document_type: str = Form(default="ITEM_PHOTO"),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.upload_item_document(
            db, user.user_id, item_donation_id, file, document_type=document_type
        )
    except (LookupError, ValueError) as exc:
        raise _handle_errors(exc) from exc


@router.post("/{item_donation_id}/submit", response_model=ItemDonationOut)
async def submit_my_item_donation(
    item_donation_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.submit_item_donation(db, user.user_id, item_donation_id)
    except (LookupError, DonorNotVerifiedError, ValueError) as exc:
        raise _handle_errors(exc) from exc
