from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.models.profiles import Address, Beneficiary, DonorProfile, NgoProfile, Program, ReceiverProfile

router = APIRouter(tags=["Profiles"])


class DonorProfileCreate(BaseModel):
    user_id: int
    full_name: str
    mobile: str
    email: str
    address_id: int | None = None


class ReceiverProfileCreate(BaseModel):
    user_id: int
    full_name: str
    mobile: str
    email: str
    address_id: int | None = None


class NgoProfileCreate(BaseModel):
    user_id: int
    ngo_name: str
    registration_number: str
    contact_person: str
    mobile: str
    address_id: int | None = None


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


@router.post("/profiles/donors", status_code=status.HTTP_201_CREATED)
async def create_donor_profile(data: DonorProfileCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(DonorProfile).where(DonorProfile.user_id == data.user_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Donor profile already exists for this user")
    donor = DonorProfile(
        user_id=data.user_id,
        full_name=data.full_name,
        mobile=data.mobile,
        email=data.email,
        address_id=data.address_id,
    )
    db.add(donor)
    await db.commit()
    await db.refresh(donor)
    return donor


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


@router.post("/profiles/receivers", status_code=status.HTTP_201_CREATED)
async def create_receiver_profile(data: ReceiverProfileCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == data.user_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Receiver profile already exists for this user")
    receiver = ReceiverProfile(
        user_id=data.user_id,
        full_name=data.full_name,
        mobile=data.mobile,
        email=data.email,
        address_id=data.address_id,
    )
    db.add(receiver)
    await db.commit()
    await db.refresh(receiver)
    return receiver


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


@router.post("/profiles/ngos", status_code=status.HTTP_201_CREATED)
async def create_ngo_profile(data: NgoProfileCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(NgoProfile).where(NgoProfile.user_id == data.user_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="NGO profile already exists for this user")
    ngo = NgoProfile(
        user_id=data.user_id,
        ngo_name=data.ngo_name,
        registration_number=data.registration_number,
        contact_person=data.contact_person,
        mobile=data.mobile,
        address_id=data.address_id,
    )
    db.add(ngo)
    await db.commit()
    await db.refresh(ngo)
    return ngo


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
