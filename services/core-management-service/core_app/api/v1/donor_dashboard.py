from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.models.profiles import NgoProfile, Program
from core_app.services.donor_dashboard_service import build_donor_dashboard
from core_app.services.donor_donations_service import build_donation_receipt, build_my_donations
from core_app.services.donor_pledges_service import build_my_pledges, build_pledges_summary_download
from core_app.services.donor_impact_service import build_impact_report_download, build_my_impact
from core_app.services.donor_recurring_gifts_service import (
    build_my_recurring_gifts,
    cancel_recurring_gift,
    pause_recurring_gift,
    resume_recurring_gift,
    update_recurring_gift,
)

router = APIRouter(tags=["Donor Dashboard"])


@router.get("/donors/me/impact")
async def get_my_impact_report(
    period: str = Query("year", description="year | last_year | month | last_month | all"),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Impact summary, charts, highlights, and journey for the authenticated donor only."""
    return await build_my_impact(db, user_id=user.user_id, period=period)


@router.get("/donors/me/impact/report/download")
async def download_my_impact_report(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Download an HTML impact report for the authenticated donor."""
    try:
        filename, content_type, html = await build_impact_report_download(
            db, user_id=user.user_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return HTMLResponse(
        content=html,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/donors/me/dashboard")
async def get_my_donor_dashboard(
    period: str = Query("year", description="month | last_month | year | last_year"),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Aggregated dashboard payload for the authenticated donor only."""
    return await build_donor_dashboard(db, user_id=user.user_id, period=period)


@router.get("/donors/me/donations")
async def get_my_donations(
    period: str = Query("year", description="year | last_year | month | last_month | all"),
    tab: str = Query("all", description="all | one_time | recurring | pledges"),
    category: str | None = Query(None, description="Cause category filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Paginated donation history for the authenticated donor only."""
    return await build_my_donations(
        db,
        user_id=user.user_id,
        period=period,
        tab=tab,
        category=category,
        page=page,
        page_size=page_size,
    )


@router.get("/donors/me/donations/{donation_key}/receipt")
async def get_my_donation_receipt(
    donation_key: str,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Download an acknowledgment receipt for a donation owned by the current donor."""
    try:
        filename, content_type, html = await build_donation_receipt(
            db, user_id=user.user_id, donation_key=donation_key
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return HTMLResponse(
        content=html,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/donors/me/pledges")
async def get_my_pledges(
    period: str = Query("year", description="year | last_year | month | last_month | all"),
    tab: str = Query("all", description="all | active | completed | cancelled"),
    category: str | None = Query(None, description="Cause category filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Paginated pledges for the authenticated donor only."""
    return await build_my_pledges(
        db,
        user_id=user.user_id,
        period=period,
        tab=tab,
        category=category,
        page=page,
        page_size=page_size,
    )


class RecurringGiftUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    frequency: str | None = None
    payment_method: str | None = None
    next_payment_date: date | None = None


@router.get("/donors/me/recurring-gifts")
async def get_my_recurring_gifts(
    period: str = Query("all", description="all | year | last_year | month | last_month"),
    tab: str = Query("all", description="all | active | paused | cancelled | completed"),
    category: str | None = Query(None, description="Cause category filter"),
    sort: str = Query("next_payment", description="next_payment | amount | start_date | status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Paginated recurring gifts for the authenticated donor only."""
    return await build_my_recurring_gifts(
        db,
        user_id=user.user_id,
        period=period,
        tab=tab,
        category=category,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.patch("/donors/me/recurring-gifts/{gift_id}")
async def patch_my_recurring_gift(
    gift_id: int,
    payload: RecurringGiftUpdate,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await update_recurring_gift(
            db,
            user_id=user.user_id,
            gift_id=gift_id,
            amount=payload.amount,
            frequency=payload.frequency,
            payment_method=payload.payment_method,
            next_payment_date=payload.next_payment_date,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/donors/me/recurring-gifts/{gift_id}/pause")
async def pause_my_recurring_gift(
    gift_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await pause_recurring_gift(db, user_id=user.user_id, gift_id=gift_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/donors/me/recurring-gifts/{gift_id}/resume")
async def resume_my_recurring_gift(
    gift_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await resume_recurring_gift(db, user_id=user.user_id, gift_id=gift_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/donors/me/recurring-gifts/{gift_id}/cancel")
async def cancel_my_recurring_gift(
    gift_id: int,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await cancel_recurring_gift(db, user_id=user.user_id, gift_id=gift_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/donors/me/pledges/summary/download")
async def download_my_pledges_summary(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    """Download an HTML pledge summary for the authenticated donor."""
    try:
        filename, content_type, html = await build_pledges_summary_download(
            db, user_id=user.user_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return HTMLResponse(
        content=html,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
