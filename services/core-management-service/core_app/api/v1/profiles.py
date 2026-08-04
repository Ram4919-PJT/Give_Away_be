from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user, require_roles
from core_app.schemas.profiles import (
    DonorProfileCreate,
    DonorProfileResponse,
    NgoProfileCreate,
    NgoProfileResponse,
    ProgramCreate,
    ProgramResponse,
    ReceiverProfileCreate,
    ReceiverProfileResponse,
)
from core_app.services import core_service

router = APIRouter(prefix="/profiles", tags=["Core - Profiles"])


@router.get("/me/donor", response_model=DonorProfileResponse | None)
async def get_my_donor_profile(
    user: TokenUser = Depends(require_roles("DONOR")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    from core_app.models.profiles import DonorProfile

    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user.user_id))
    return result.scalar_one_or_none()


@router.post("/donor", response_model=DonorProfileResponse, status_code=201)
async def create_donor_profile(
    payload: DonorProfileCreate,
    user: TokenUser = Depends(require_roles("DONOR")),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.get_or_create_donor_profile(db, user, payload)


@router.post("/receiver", response_model=ReceiverProfileResponse, status_code=201)
async def create_receiver_profile(
    payload: ReceiverProfileCreate,
    user: TokenUser = Depends(require_roles("RECEIVER")),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.get_or_create_receiver_profile(db, user, payload)


@router.post("/ngo", response_model=NgoProfileResponse, status_code=201)
async def create_ngo_profile(
    payload: NgoProfileCreate,
    user: TokenUser = Depends(require_roles("NGO")),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.get_or_create_ngo_profile(db, user, payload)


@router.get("/programs", response_model=list[ProgramResponse])
async def list_programs(
    _user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.list_programs(db)


@router.post("/programs", response_model=ProgramResponse, status_code=201)
async def create_program(
    payload: ProgramCreate,
    user: TokenUser = Depends(require_roles("NGO")),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.create_program(db, user, payload)
