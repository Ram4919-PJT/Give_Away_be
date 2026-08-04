from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.exceptions import ConflictError, NotFoundError
from core_app.dependencies.auth import TokenUser
from core_app.models.donations import Donation, DonationStatusHistory, MoneyDonationDetail
from core_app.models.enums import DonationStatus, DonationType, ProfileStatus
from core_app.models.profiles import DonorProfile, NgoProfile, Program, ReceiverProfile
from core_app.models.verification import VerificationRequest
from core_app.schemas.donations import DonationCreate, VerificationRequestCreate
from core_app.schemas.profiles import (
    DonorProfileCreate,
    NgoProfileCreate,
    ProgramCreate,
    ReceiverProfileCreate,
)


async def get_or_create_donor_profile(
    db: AsyncSession, user: TokenUser, payload: DonorProfileCreate
) -> DonorProfile:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user.user_id))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    profile = DonorProfile(
        user_id=user.user_id,
        organization_name=payload.organization_name,
        pan_number=payload.pan_number,
        status=ProfileStatus.ACTIVE,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_or_create_receiver_profile(
    db: AsyncSession, user: TokenUser, payload: ReceiverProfileCreate
) -> ReceiverProfile:
    result = await db.execute(
        select(ReceiverProfile).where(ReceiverProfile.user_id == user.user_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    profile = ReceiverProfile(
        user_id=user.user_id,
        household_size=payload.household_size,
        monthly_income=payload.monthly_income,
        status=ProfileStatus.ACTIVE,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def get_or_create_ngo_profile(
    db: AsyncSession, user: TokenUser, payload: NgoProfileCreate
) -> NgoProfile:
    result = await db.execute(select(NgoProfile).where(NgoProfile.user_id == user.user_id))
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError("NGO profile already exists for this user")

    profile = NgoProfile(
        user_id=user.user_id,
        registration_number=payload.registration_number,
        organization_name=payload.organization_name,
        focus_area=payload.focus_area,
        status=ProfileStatus.ACTIVE,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def list_programs(db: AsyncSession) -> list[Program]:
    result = await db.execute(select(Program).order_by(Program.created_at.desc()))
    return list(result.scalars().all())


async def create_program(
    db: AsyncSession, user: TokenUser, payload: ProgramCreate
) -> Program:
    result = await db.execute(select(NgoProfile).where(NgoProfile.user_id == user.user_id))
    ngo_profile = result.scalar_one_or_none()
    if not ngo_profile:
        raise NotFoundError("NGO profile not found")

    program = Program(
        ngo_profile_id=ngo_profile.ngo_profile_id,
        title=payload.title,
        description=payload.description,
    )
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program


async def list_donations(db: AsyncSession, user: TokenUser) -> list[Donation]:
    query = select(Donation).order_by(Donation.created_at.desc())
    if user.role != "SUPER_ADMIN":
        query = query.where(Donation.donor_user_id == user.user_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_donation(
    db: AsyncSession, user: TokenUser, payload: DonationCreate
) -> Donation:
    donation = Donation(
        donor_user_id=user.user_id,
        donation_type=payload.donation_type,
        status=DonationStatus.SUBMITTED,
        notes=payload.notes,
    )
    db.add(donation)
    await db.flush()

    if payload.donation_type == DonationType.MONEY:
        if payload.amount is None:
            raise ValueError("amount is required for money donations")
        db.add(
            MoneyDonationDetail(
                donation_id=donation.donation_id,
                amount=payload.amount,
                currency=payload.currency,
            )
        )

    db.add(
        DonationStatusHistory(
            donation_id=donation.donation_id,
            from_status=DonationStatus.DRAFT,
            to_status=DonationStatus.SUBMITTED,
            changed_by=user.user_id,
        )
    )
    await db.commit()
    await db.refresh(donation)
    return donation


async def list_verification_requests(
    db: AsyncSession, user: TokenUser
) -> list[VerificationRequest]:
    query = select(VerificationRequest).order_by(VerificationRequest.submitted_at.desc())
    if user.role != "SUPER_ADMIN":
        query = query.where(VerificationRequest.user_id == user.user_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_verification_request(
    db: AsyncSession, user: TokenUser, payload: VerificationRequestCreate
) -> VerificationRequest:
    request = VerificationRequest(
        user_id=user.user_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        notes=payload.notes,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request
