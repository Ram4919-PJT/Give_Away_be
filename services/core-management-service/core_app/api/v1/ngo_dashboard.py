from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.dependencies.ngo_auth import require_verified_ngo_profile
from core_app.models.profiles import Beneficiary, NgoProfile
from core_app.services.ngo_dashboard_service import build_ngo_dashboard
from core_app.services.ngo_service import is_ngo_verified, require_ngo_profile

router = APIRouter(tags=["NGO Dashboard"])


class NgoBeneficiaryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=0, le=120)
    details: str | None = None


@router.get("/ngos/me/dashboard")
async def get_my_ngo_dashboard(
    period: str = Query("month", description="week | month | last_3_months | year"),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("NGO")),
):
    try:
        return await build_ngo_dashboard(db, user_id=user.user_id, period=period)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/ngos/me/profile")
async def get_my_ngo_profile(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("NGO")),
):
    try:
        profile = await require_ngo_profile(db, user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {
        "ngo_id": profile.ngo_id,
        "user_id": profile.user_id,
        "ngo_name": profile.ngo_name,
        "registration_number": profile.registration_number,
        "contact_person": profile.contact_person,
        "mobile": profile.mobile,
        "verification_status": profile.verification_status,
        "verified": is_ngo_verified(profile),
    }


@router.get("/ngos/me/beneficiaries")
async def list_my_beneficiaries(
    db: AsyncSession = Depends(get_db),
    profile: NgoProfile = Depends(require_verified_ngo_profile),
):
    rows = (
        await db.execute(select(Beneficiary).where(Beneficiary.ngo_id == profile.ngo_id))
    ).scalars().all()
    return rows


@router.post("/ngos/me/beneficiaries", status_code=status.HTTP_201_CREATED)
async def create_my_beneficiary(
    data: NgoBeneficiaryCreate,
    db: AsyncSession = Depends(get_db),
    profile: NgoProfile = Depends(require_verified_ngo_profile),
):
    beneficiary = Beneficiary(
        ngo_id=profile.ngo_id,
        name=data.name.strip(),
        age=data.age,
        details=(data.details or "").strip() or None,
    )
    db.add(beneficiary)
    await db.commit()
    await db.refresh(beneficiary)
    return beneficiary
