from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.schemas.item_donation import (
    ItemDonationRequestCreate,
    ItemDonationRequestOut,
    ItemRequestAction,
)
from core_app.services import item_donation_service as service

donor_router = APIRouter(prefix="/donors/me/item-requests", tags=["Donor Item Requests"])
receiver_router = APIRouter(prefix="/receivers/me/item-requests", tags=["Receiver Item Requests"])


@donor_router.get("", response_model=list[ItemDonationRequestOut])
async def list_donor_item_requests(
    item_id: int | None = Query(default=None, alias="item"),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.list_donor_requests(db, user.user_id, item_donation_id=item_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@donor_router.post("/{request_id}/respond", response_model=ItemDonationRequestOut)
async def respond_to_item_request(
    request_id: int,
    data: ItemRequestAction,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.respond_to_request(db, user.user_id, request_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@donor_router.post("/{request_id}/complete", response_model=ItemDonationRequestOut)
async def complete_item_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await service.complete_request_fulfillment(db, user.user_id, request_id, as_donor=True)
    except (LookupError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(exc, ValueError) else status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@receiver_router.get("", response_model=list[ItemDonationRequestOut])
async def list_my_item_requests(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await service.list_receiver_requests(db, user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@receiver_router.post("", response_model=ItemDonationRequestOut, status_code=status.HTTP_201_CREATED)
async def create_item_request(
    data: ItemDonationRequestCreate,
    item_donation_id: int = Query(..., description="Item to request"),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Physical item requests are not available for receivers. Please apply for financial assistance instead.",
    )


@receiver_router.post("/{request_id}/cancel", response_model=ItemDonationRequestOut)
async def cancel_item_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("RECEIVER")),
):
    try:
        return await service.cancel_item_request(db, user.user_id, request_id)
    except (LookupError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST if isinstance(exc, ValueError) else status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
