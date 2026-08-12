from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.models.profiles import NgoProfile, Program
from core_app.services.donor_dashboard_service import build_donor_dashboard

router = APIRouter(tags=["Donor Dashboard"])


@router.get("/donors/me/dashboard")
async def get_my_donor_dashboard(
    period: str = Query("year", description="month | last_month | year | last_year"),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Aggregated dashboard payload for the authenticated donor only."""
    return await build_donor_dashboard(db, user_id=user.user_id, period=period)


@router.get("/search")
async def search_causes_and_ngos(
    q: str = Query("", min_length=0, max_length=120),
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR", "RECEIVER", "NGO", "SUPER_ADMIN")),
):
    """Search programs (causes/campaigns) and NGO partners."""
    query = (q or "").strip()
    if not query:
        return {"programs": [], "ngos": [], "query": query}

    pattern = f"%{query}%"
    programs_res = await db.execute(
        select(Program)
        .where(
            or_(
                Program.program_name.ilike(pattern),
                Program.category.ilike(pattern),
                Program.description.ilike(pattern),
            )
        )
        .limit(limit)
    )
    ngos_res = await db.execute(
        select(NgoProfile)
        .where(
            or_(
                NgoProfile.ngo_name.ilike(pattern),
                NgoProfile.contact_person.ilike(pattern),
                NgoProfile.registration_number.ilike(pattern),
            )
        )
        .limit(limit)
    )

    programs = [
        {
            "program_id": p.program_id,
            "program_name": p.program_name,
            "category": p.category,
            "description": p.description,
            "status": p.status,
            "type": "program",
        }
        for p in programs_res.scalars().all()
    ]
    ngos = [
        {
            "ngo_id": n.ngo_id,
            "ngo_name": n.ngo_name,
            "contact_person": n.contact_person,
            "verification_status": n.verification_status,
            "type": "ngo",
        }
        for n in ngos_res.scalars().all()
    ]
    return {"programs": programs, "ngos": ngos, "query": query}
