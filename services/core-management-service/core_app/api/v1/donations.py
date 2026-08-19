from datetime import date, time
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.integrations.notification_client import notify_user
from core_app.models.donations import DonationStatusHistory, ItemDonation, MoneyDonation, PickupSchedule
from core_app.models.profiles import DonorProfile, Program

router = APIRouter(prefix="/donations", tags=["Donations"])


class MoneyDonationCreate(BaseModel):
    donor_id: int
    program_id: int
    amount: float


class ItemDonationCreate(BaseModel):
    donor_id: int
    category: str
    description: str
    quantity: int
    pickup_address_id: int


class PickupScheduleCreate(BaseModel):
    item_donation_id: int
    pickup_date: str  # YYYY-MM-DD
    pickup_time: str  # HH:MM:SS


@router.get("/money")
async def list_money_donations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MoneyDonation))
    return result.scalars().all()


@router.post("/money", status_code=status.HTTP_201_CREATED)
async def create_money_donation(data: MoneyDonationCreate, db: AsyncSession = Depends(get_db)):
    donation = MoneyDonation(
        donor_id=data.donor_id,
        program_id=data.program_id,
        amount=data.amount,
        payment_status="CONFIRMED",
    )
    db.add(donation)
    await db.commit()
    await db.refresh(donation)
    
    history = DonationStatusHistory(donation_id=donation.donation_id, donation_type="MONEY", status="CONFIRMED")
    db.add(history)
    await db.commit()

    donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == data.donor_id))
    donor = donor_result.scalar_one_or_none()
    program_result = await db.execute(select(Program).where(Program.program_id == data.program_id))
    program = program_result.scalar_one_or_none()
    if donor:
        program_name = program.program_name if program else "the selected program"
        await notify_user(
            user_id=donor.user_id,
            title="Donation received",
            message=f"Thank you! Your donation of ₹{data.amount:,.0f} to {program_name} has been confirmed.",
            notification_type="DONATION",
            event_type="PAYMENT_SUCCESS",
            related_entity_type="MONEY_DONATION",
            related_entity_id=donation.donation_id,
            action_url="/dashboard/donor-my-donations",
            recipient_email=donor.email,
            recipient_name=donor.full_name,
            template_data={
                "donation_id": donation.donation_id,
                "campaign_name": program_name,
                "amount_display": f"₹{data.amount:,.0f}",
                "status": "CONFIRMED",
            },
            idempotency_key=f"donation-confirmed:{donation.donation_id}",
        )
    return donation


@router.get("/items")
async def list_item_donations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ItemDonation))
    return result.scalars().all()


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item_donation(data: ItemDonationCreate, db: AsyncSession = Depends(get_db)):
    """Legacy endpoint — creates a draft donation. Prefer POST /donors/me/item-donations."""
    item_don = ItemDonation(
        donor_id=data.donor_id,
        category=data.category,
        description=data.description,
        quantity=data.quantity,
        pickup_address_id=data.pickup_address_id,
        status="DRAFT",
    )
    db.add(item_don)
    await db.commit()
    await db.refresh(item_don)
    
    history = DonationStatusHistory(donation_id=item_don.item_donation_id, donation_type="ITEM", status="DRAFT")
    db.add(history)
    await db.commit()
    return item_don


@router.get("/pickup-schedules")
async def list_pickup_schedules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PickupSchedule))
    return result.scalars().all()


@router.post("/pickup-schedules", status_code=status.HTTP_201_CREATED)
async def schedule_pickup(data: PickupScheduleCreate, db: AsyncSession = Depends(get_db)):
    try:
        p_date = date.fromisoformat(data.pickup_date)
        p_time = time.fromisoformat(data.pickup_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format. Use YYYY-MM-DD and HH:MM:SS")

    sched = PickupSchedule(
        item_donation_id=data.item_donation_id,
        pickup_date=p_date,
        pickup_time=p_time,
        status="SCHEDULED",
    )
    db.add(sched)
    
    # Update item donation status
    item_res = await db.execute(select(ItemDonation).where(ItemDonation.item_donation_id == data.item_donation_id))
    item = item_res.scalar_one_or_none()
    if item:
        item.status = "PICKUP_SCHEDULED"

    await db.commit()
    await db.refresh(sched)

    if item:
        donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == item.donor_id))
        donor = donor_result.scalar_one_or_none()
        if donor:
            await notify_user(
                user_id=donor.user_id,
                title="Pickup scheduled",
                message=(
                    f"Item pickup for your {item.category} donation is scheduled on "
                    f"{p_date.isoformat()} at {p_time.strftime('%H:%M')}."
                ),
                notification_type="DONATION",
                related_entity_type="ITEM_DONATION",
                related_entity_id=item.item_donation_id,
                action_url="/dashboard/donor-notifications",
            )
    return sched


@router.get("/status-history")
async def list_donation_status_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DonationStatusHistory))
    return result.scalars().all()
