"""Server-side aggregations for the authenticated NGO dashboard."""

from __future__ import annotations

from calendar import month_abbr
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.applications import NgoFundRequest, NgoItemRequest
from core_app.models.funds import Allocation
from core_app.models.inventory import InventoryItem
from core_app.models.profiles import Beneficiary, NgoProfile
from core_app.services.ngo_service import is_ngo_suspended, is_ngo_verified

APPROVED_FUND = {"APPROVED", "FULFILLED", "COMPLETED"}
PENDING_FUND = {"SUBMITTED", "UNDER_REVIEW", "PENDING", "DRAFT"}
APPROVED_ITEM = {"APPROVED", "FULFILLED", "COMPLETED", "ALLOCATED"}
PENDING_ITEM = {"SUBMITTED", "UNDER_REVIEW", "PENDING", "DRAFT"}

CATEGORY_COLORS = {
    "Food": "#F97316",
    "Clothing": "#8B5CF6",
    "Medical": "#20B878",
    "Education": "#1268E8",
    "Furniture": "#0EA5E9",
    "Funds": "#1268E8",
    "Other": "#94A3B8",
}


def _as_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _as_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _status_label(status: str | None) -> str:
    raw = (status or "SUBMITTED").upper()
    mapping = {
        "SUBMITTED": "Submitted",
        "UNDER_REVIEW": "Under Review",
        "APPROVED": "Approved",
        "REJECTED": "Rejected",
        "FULFILLED": "Fulfilled",
        "COMPLETED": "Completed",
        "CANCELLED": "Cancelled",
        "DRAFT": "Draft",
        "ALLOCATED": "Approved",
        "PENDING": "Under Review",
    }
    return mapping.get(raw, raw.replace("_", " ").title())


def _period_bounds(period: str, now: datetime) -> tuple[datetime, datetime]:
    p = (period or "month").lower().replace(" ", "_")
    end = now

    if p in {"week", "this_week"}:
        start = now - timedelta(days=now.weekday())
        start = datetime(start.year, start.month, start.day)
        return start, end

    if p in {"last_3_months", "quarter", "3_months"}:
        month = now.month - 2
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        return datetime(year, month, 1), end

    if p in {"year", "this_year"}:
        return datetime(now.year, 1, 1), end

    # default: this month
    return datetime(now.year, now.month, 1), end


def _relative_time(dt: datetime | None, now: datetime) -> str:
    if not dt:
        return "Recently"
    delta = now - dt
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "Just now"
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    return dt.strftime("%d %b %Y")


def _request_timestamp(req: Any) -> datetime | None:
    for attr in ("submitted_at", "created_at", "updated_at"):
        dt = _as_dt(getattr(req, attr, None))
        if dt:
            return dt
    return None


def _verification_message(status: str | None, suspended: bool) -> str:
    if suspended:
        return "Your NGO account is suspended. Contact platform support for assistance."
    raw = (status or "REGISTERED").upper()
    if raw == "REJECTED":
        return "Your verification was rejected. Review the feedback and resubmit your documents."
    if raw in {"DOCUMENTS_SUBMITTED", "UNDER_REVIEW", "SUBMITTED", "PENDING"}:
        return "Your documents are under review. Operational features unlock after verification."
    if raw == "REGISTERED":
        return "Complete NGO verification to access donations, funds, inventory, beneficiaries, and reports."
    return "Complete NGO verification to unlock all NGO features."


def _build_unverified_dashboard(ngo: NgoProfile, period: str) -> dict[str, Any]:
    status = (ngo.verification_status or "REGISTERED").upper()
    suspended = is_ngo_suspended(ngo)
    return {
        "profile": {
            "ngo_id": ngo.ngo_id,
            "ngo_name": ngo.ngo_name,
            "contact_person": ngo.contact_person,
            "mobile": ngo.mobile,
            "verification_status": ngo.verification_status,
            "verified": False,
            "suspended": suspended,
        },
        "period": period,
        "access_level": "unverified",
        "verification_message": _verification_message(status, suspended),
        "kpis": [],
        "donation_trend": [],
        "donations_by_type": [],
        "recent_activity": [],
        "pending_requests": [],
        "impact_snapshot": {
            "beneficiaries_helped": 0,
            "funds_distributed": 0,
            "items_distributed": 0,
            "approved_requests": 0,
        },
        "stats": {
            "total_funds_received": 0,
            "total_beneficiaries": 0,
            "pending_requests": 0,
            "total_item_units": 0,
            "approved_requests": 0,
        },
    }


async def build_ngo_dashboard(
    db: AsyncSession,
    *,
    user_id: int,
    period: str = "month",
) -> dict[str, Any]:
    ngo = (await db.execute(select(NgoProfile).where(NgoProfile.user_id == user_id))).scalar_one_or_none()
    if not ngo:
        raise LookupError("NGO profile not found")

    now = datetime.utcnow()
    period_start, period_end = _period_bounds(period, now)
    verified = is_ngo_verified(ngo)

    if not verified or is_ngo_suspended(ngo):
        return _build_unverified_dashboard(ngo, period)

    fund_rows = (
        await db.execute(select(NgoFundRequest).where(NgoFundRequest.ngo_id == ngo.ngo_id))
    ).scalars().all()
    item_rows = (
        await db.execute(select(NgoItemRequest).where(NgoItemRequest.ngo_id == ngo.ngo_id))
    ).scalars().all()
    beneficiaries = (
        await db.execute(select(Beneficiary).where(Beneficiary.ngo_id == ngo.ngo_id))
    ).scalars().all()

    item_ids = [r.request_id for r in item_rows]
    allocations: list[Allocation] = []
    if item_ids:
        allocations = (
            await db.execute(select(Allocation).where(Allocation.ngo_request_id.in_(item_ids)))
        ).scalars().all()

    inventory_map: dict[int, InventoryItem] = {}
    if allocations:
        inv_ids = {a.item_id for a in allocations}
        inv_rows = (
            await db.execute(select(InventoryItem).where(InventoryItem.item_id.in_(inv_ids)))
        ).scalars().all()
        inventory_map = {row.item_id: row for row in inv_rows}

    total_funds_received = sum(
        _as_float(r.amount_requested)
        for r in fund_rows
        if (r.status or "").upper() in APPROVED_FUND
    )
    pending_fund_requests = sum(1 for r in fund_rows if (r.status or "").upper() in PENDING_FUND)
    pending_item_requests = sum(1 for r in item_rows if (r.status or "").upper() in PENDING_ITEM)
    approved_requests = sum(
        1 for r in fund_rows + item_rows if (r.status or "").upper() in APPROVED_FUND | APPROVED_ITEM
    )
    total_item_units = sum(a.quantity_allocated for a in allocations)

    kpis = [
        {
            "id": "funds_received",
            "label": "Funds Received",
            "value": round(total_funds_received, 2),
            "display": f"₹{total_funds_received:,.0f}",
            "hint": "Approved fund assistance",
            "accent": "blue",
        },
        {
            "id": "beneficiaries",
            "label": "Beneficiaries",
            "value": len(beneficiaries),
            "display": str(len(beneficiaries)),
            "hint": "People your NGO supports",
            "accent": "purple",
        },
        {
            "id": "pending_verifications",
            "label": "Pending Requests",
            "value": pending_fund_requests + pending_item_requests,
            "display": str(pending_fund_requests + pending_item_requests),
            "hint": "Awaiting review",
            "accent": "orange",
        },
        {
            "id": "items_received",
            "label": "Items Allocated",
            "value": total_item_units,
            "display": str(total_item_units),
            "hint": "Units allocated to your NGO",
            "accent": "teal",
        },
        {
            "id": "approved_requests",
            "label": "Approved Requests",
            "value": approved_requests,
            "display": str(approved_requests),
            "hint": "Fund and item requests",
            "accent": "green",
        },
    ]

    # Donation / support trend from allocations + approved funds in period
    trend_buckets: dict[str, float] = defaultdict(float)
    for alloc in allocations:
        dt = _as_dt(alloc.allocated_at)
        if not dt or dt < period_start or dt > period_end:
            continue
        key = dt.strftime("%Y-%m-%d")
        trend_buckets[key] += float(alloc.quantity_allocated)

    for fund in fund_rows:
        if (fund.status or "").upper() not in APPROVED_FUND:
            continue
        dt = _request_timestamp(fund)
        if not dt or dt < period_start or dt > period_end:
            continue
        key = dt.strftime("%Y-%m-%d")
        trend_buckets[key] += _as_float(fund.amount_requested)

    donation_trend = []
    if trend_buckets:
        for key in sorted(trend_buckets.keys()):
            dt = datetime.strptime(key, "%Y-%m-%d")
            donation_trend.append({
                "label": dt.strftime("%d %b"),
                "value": round(trend_buckets[key], 2),
                "date": key,
            })
    elif period in {"year", "this_year"}:
        for m in range(1, now.month + 1):
            donation_trend.append({"label": month_abbr[m], "value": 0, "date": f"{now.year}-{m:02d}"})
    else:
        cursor = period_start
        while cursor <= period_end:
            donation_trend.append({
                "label": cursor.strftime("%d %b"),
                "value": 0,
                "date": cursor.strftime("%Y-%m-%d"),
            })
            cursor += timedelta(days=1)
            if len(donation_trend) > 31:
                break

    # Support by type
    type_totals: dict[str, float] = defaultdict(float)
    for fund in fund_rows:
        if (fund.status or "").upper() in APPROVED_FUND:
            type_totals["Funds"] += _as_float(fund.amount_requested)
    for alloc in allocations:
        item = inventory_map.get(alloc.item_id)
        cat = (item.category if item else "Other") or "Other"
        type_totals[cat] += float(alloc.quantity_allocated)
    for item_req in item_rows:
        if (item_req.status or "").upper() in APPROVED_ITEM:
            cat = item_req.item_category or "Other"
            type_totals[cat] += float(item_req.quantity_requested)

    donations_by_type = []
    for name, value in sorted(type_totals.items(), key=lambda x: -x[1]):
        if value <= 0:
            continue
        donations_by_type.append({
            "name": name,
            "value": round(value, 2),
            "color": CATEGORY_COLORS.get(name, CATEGORY_COLORS["Other"]),
        })

    # Recent activity
    activities: list[dict[str, Any]] = []
    for fund in fund_rows:
        dt = _request_timestamp(fund) or now
        activities.append({
            "id": f"fund-{fund.request_id}",
            "type": "fund_request",
            "title": "Fund request updated",
            "description": fund.purpose[:120] if fund.purpose else "Financial assistance request",
            "amount": _as_float(fund.amount_requested),
            "amount_display": f"₹{_as_float(fund.amount_requested):,.0f}",
            "status": _status_label(fund.status),
            "timestamp": dt.isoformat(),
            "relative_time": _relative_time(dt, now),
        })
    for item in item_rows:
        dt = _request_timestamp(item) or now
        activities.append({
            "id": f"item-{item.request_id}",
            "type": "item_request",
            "title": "Item request updated",
            "description": f"{item.item_category} · {item.quantity_requested} units",
            "amount": item.quantity_requested,
            "amount_display": f"{item.quantity_requested} items",
            "status": _status_label(item.status),
            "timestamp": dt.isoformat(),
            "relative_time": _relative_time(dt, now),
        })
    for alloc in allocations:
        dt = _as_dt(alloc.allocated_at) or now
        item = inventory_map.get(alloc.item_id)
        activities.append({
            "id": f"alloc-{alloc.allocation_id}",
            "type": "allocation",
            "title": "Items allocated",
            "description": item.description[:100] if item and item.description else "Inventory allocation",
            "amount": alloc.quantity_allocated,
            "amount_display": f"{alloc.quantity_allocated} units",
            "status": "Fulfilled",
            "timestamp": dt.isoformat(),
            "relative_time": _relative_time(dt, now),
        })

    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    recent_activity = activities[:8]

    # Pending requests for dashboard panel
    pending_items = []
    for item in item_rows:
        if (item.status or "").upper() not in PENDING_ITEM:
            continue
        pending_items.append({
            "id": item.request_id,
            "request_type": "item",
            "title": item.item_category,
            "quantity": item.quantity_requested,
            "amount_display": f"{item.quantity_requested} items",
            "status": _status_label(item.status),
            "relative_time": _relative_time(_request_timestamp(item), now),
        })
    for fund in fund_rows:
        if (fund.status or "").upper() not in PENDING_FUND:
            continue
        pending_items.append({
            "id": fund.request_id,
            "request_type": "fund",
            "title": fund.purpose[:80] if fund.purpose else "Fund request",
            "amount": _as_float(fund.amount_requested),
            "amount_display": f"₹{_as_float(fund.amount_requested):,.0f}",
            "status": _status_label(fund.status),
            "relative_time": _relative_time(_request_timestamp(fund), now),
        })
    pending_items = pending_items[:6]

    impact = {
        "beneficiaries_helped": len(beneficiaries),
        "funds_distributed": round(total_funds_received, 2),
        "items_distributed": total_item_units,
        "approved_requests": approved_requests,
    }

    return {
        "profile": {
            "ngo_id": ngo.ngo_id,
            "ngo_name": ngo.ngo_name,
            "contact_person": ngo.contact_person,
            "mobile": ngo.mobile,
            "verification_status": ngo.verification_status,
            "verified": verified,
            "suspended": False,
        },
        "period": period,
        "access_level": "verified",
        "kpis": kpis[:6],
        "donation_trend": donation_trend,
        "donations_by_type": donations_by_type,
        "recent_activity": recent_activity,
        "pending_requests": pending_items,
        "impact_snapshot": impact,
        "stats": {
            "total_funds_received": round(total_funds_received, 2),
            "total_beneficiaries": len(beneficiaries),
            "pending_requests": pending_fund_requests + pending_item_requests,
            "total_item_units": total_item_units,
            "approved_requests": approved_requests,
        },
    }
