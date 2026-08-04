from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user, require_roles
from core_app.schemas.donations import DonationCreate, DonationResponse
from core_app.services import core_service

router = APIRouter(prefix="/donations", tags=["Core - Donations"])


@router.get("", response_model=list[DonationResponse])
async def list_donations(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.list_donations(db, user)


@router.post("", response_model=DonationResponse, status_code=201)
async def create_donation(
    payload: DonationCreate,
    user: TokenUser = Depends(require_roles("DONOR")),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.create_donation(db, user, payload)
