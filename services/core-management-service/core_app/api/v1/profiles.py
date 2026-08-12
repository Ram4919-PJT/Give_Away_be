from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.models.profiles import Address, Beneficiary, DonorProfile, NgoProfile, Program, ReceiverProfile

router = APIRouter(tags=["Profiles"])


# --- Addresses ---
@router.get("/addresses")
async def list_addresses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Address))
    return result.scalars().all()


# --- Donor Profiles ---
@router.get("/profiles/donors")
async def list_donor_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DonorProfile))
    return result.scalars().all()


@router.get("/profiles/donors/{donor_id}")
async def get_donor_profile(donor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == donor_id))
    donor = result.scalar_one_or_none()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor profile not found")
    return donor


# --- Receiver Profiles ---
@router.get("/profiles/receivers")
async def list_receiver_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReceiverProfile))
    return result.scalars().all()


@router.get("/profiles/receivers/{receiver_id}")
async def get_receiver_profile(receiver_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReceiverProfile).where(ReceiverProfile.receiver_id == receiver_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Receiver profile not found")
    return rec


# --- NGO Profiles ---
@router.get("/profiles/ngos")
async def list_ngo_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NgoProfile))
    return result.scalars().all()


@router.get("/profiles/ngos/{ngo_id}")
async def get_ngo_profile(ngo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NgoProfile).where(NgoProfile.ngo_id == ngo_id))
    ngo = result.scalar_one_or_none()
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO profile not found")
    return ngo


# --- Beneficiaries ---
@router.get("/beneficiaries")
async def list_beneficiaries(ngo_id: int | None = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(Beneficiary)
    if ngo_id:
        stmt = stmt.where(Beneficiary.ngo_id == ngo_id)
    result = await db.execute(stmt)
    return result.scalars().all()


# --- Programs ---
@router.get("/programs")
async def list_programs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Program))
    return result.scalars().all()
