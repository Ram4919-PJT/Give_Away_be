"""Public read-only endpoints (no auth required)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.models.applications import AssistanceApplication
from core_app.models.donations import ItemDonation, MoneyDonation
from core_app.models.profiles import DonorProfile, NgoProfile, Program, ReceiverProfile
from core_app.models.inventory import InventoryItem
from core_app.services import geocoding_service
from core_app.services import geocoding_service

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/programs")
async def list_public_programs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Program).where(Program.status == "ACTIVE").order_by(Program.program_id)
    )
    programs = result.scalars().all()
    return [
        {
            "program_id": p.program_id,
            "program_name": p.program_name,
            "description": p.description,
            "category": p.category,
            "status": p.status,
        }
        for p in programs
    ]


@router.get("/stats")
async def get_public_stats(db: AsyncSession = Depends(get_db)):
    donor_count = (await db.execute(select(func.count()).select_from(DonorProfile))).scalar() or 0
    receiver_count = (await db.execute(select(func.count()).select_from(ReceiverProfile))).scalar() or 0
    ngo_count = (
        await db.execute(
            select(func.count()).select_from(NgoProfile).where(NgoProfile.verification_status == "VERIFIED")
        )
    ).scalar() or 0
    money_count = (await db.execute(select(func.count()).select_from(MoneyDonation))).scalar() or 0
    item_count = (await db.execute(select(func.count()).select_from(ItemDonation))).scalar() or 0
    program_count = (
        await db.execute(select(func.count()).select_from(Program).where(Program.status == "ACTIVE"))
    ).scalar() or 0
    inventory_qty = (
        await db.execute(select(func.coalesce(func.sum(InventoryItem.quantity), 0)))
    ).scalar() or 0

    return {
        "donors": int(donor_count),
        "receivers": int(receiver_count),
        "verified_ngos": int(ngo_count),
        "money_donations": int(money_count),
        "item_donations": int(item_count),
        "donations_delivered": int(money_count) + int(item_count),
        "active_programs": int(program_count),
        "inventory_units": int(inventory_qty),
        "lives_impacted": int(receiver_count),
    }


@router.get("/location/search")
async def public_search_locations(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(6, ge=1, le=8),
):
    """Public place search for manual location selection (rate-limited via Nominatim)."""
    try:
        results = await geocoding_service.forward_geocode_search(q, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Location search is temporarily unavailable.",
        ) from exc
    return {"success": True, "query": q.strip(), "results": results}
