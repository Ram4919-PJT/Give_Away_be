"""Authenticated donor recurring gifts list, summary, impact, and mutations."""

from __future__ import annotations

from calendar import month_abbr
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import engine
from core_app.models.profiles import DonorProfile, Program
from core_app.models.recurring_gifts import RecurringGift
from core_app.services.donor_dashboard_service import (
    CATEGORY_COLORS,
    CATEGORY_IMAGES,
    RUPEES_PER_LIFE,
    _normalize_category,
    _period_bounds,
)

ACTIVE = {"ACTIVE"}
PAUSED = {"PAUSED"}
CANCELLED = {"CANCELLED", "CANCELED"}
COMPLETED = {"COMPLETED", "FULFILLED"}

FREQUENCIES = ("DAILY", "WEEKLY", "MONTHLY", "QUARTERLY", "YEARLY")
FREQUENCY_META = [
    {"id": "DAILY", "label": "Daily", "short": "day"},
    {"id": "WEEKLY", "label": "Weekly", "short": "week"},
    {"id": "MONTHLY", "label": "Monthly", "short": "month"},
    {"id": "QUARTERLY", "label": "Quarterly", "short": "quarter"},
    {"id": "YEARLY", "label": "Yearly", "short": "year"},
]
PAYMENT_METHODS = ("UPI AutoPay", "UPI", "Card", "Net Banking", "Wallet")

ENSURE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS recurring_gifts (
    gift_id BIGSERIAL PRIMARY KEY,
    donor_id BIGINT NOT NULL REFERENCES donor_profiles(donor_id),
    program_id BIGINT NOT NULL REFERENCES programs(program_id),
    organization_name VARCHAR(150) NOT NULL DEFAULT 'Aja Abayahastham',
    amount DECIMAL(10, 2) NOT NULL,
    frequency VARCHAR(20) NOT NULL DEFAULT 'MONTHLY',
    start_date DATE NOT NULL,
    next_payment_date DATE,
    payments_made INT NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    payment_method VARCHAR(50),
    paused_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _empty_summary() -> dict[str, Any]:
    return {
        "active_count": 0,
        "monthly_commitment": 0.0,
        "total_contributed": 0.0,
        "donations_count": 0,
        "next_payment_date": None,
        "next_payment_label": None,
        "next_payment_amount": 0.0,
        "lives_impacted": None,
        "causes_supported": 0,
    }


def _empty_impact() -> dict[str, Any]:
    return {
        "lives_impacted": None,
        "causes_supported": 0,
        "by_category": [],
        "monthly_total": 0.0,
    }


_table_ready = False


async def ensure_recurring_gifts_table(db: AsyncSession | None = None) -> None:
    global _table_ready
    if _table_ready:
        return
    async with engine.begin() as conn:
        await conn.execute(text(ENSURE_TABLE_SQL))
    _table_ready = True


async def _resolve_donor(db: AsyncSession, user_id: int) -> DonorProfile | None:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    return result.scalar_one_or_none()


def _add_months(start: date, months: int) -> date:
    y = start.year + (start.month - 1 + months) // 12
    m = (start.month - 1 + months) % 12 + 1
    days = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    d = min(start.day, days[m - 1])
    return date(y, m, d)


def next_date_from(start: date, frequency: str) -> date:
    key = (frequency or "MONTHLY").upper()
    if key == "DAILY":
        return start + timedelta(days=1)
    if key == "WEEKLY":
        return start + timedelta(days=7)
    if key == "QUARTERLY":
        return _add_months(start, 3)
    if key == "YEARLY":
        return _add_months(start, 12)
    return _add_months(start, 1)


def _monthly_equivalent(amount: float, frequency: str) -> float:
    key = (frequency or "MONTHLY").upper()
    if key == "DAILY":
        return round(amount * 30.0, 2)
    if key == "WEEKLY":
        return round(amount * 52.0 / 12.0, 2)
    if key == "QUARTERLY":
        return round(amount / 3.0, 2)
    if key == "YEARLY":
        return round(amount / 12.0, 2)
    return round(amount, 2)


def _frequency_meta(raw: str | None) -> dict[str, str]:
    key = (raw or "MONTHLY").upper()
    for item in FREQUENCY_META:
        if item["id"] == key:
            return item
    return {"id": "MONTHLY", "label": "Monthly", "short": "month"}


def _status_label(raw: str | None) -> str:
    s = (raw or "").upper()
    if s in PAUSED:
        return "Paused"
    if s in CANCELLED:
        return "Cancelled"
    if s in COMPLETED:
        return "Completed"
    return "Active"


def _relative_to_now(target: date | None, *, now: date) -> str | None:
    if not target:
        return None
    delta = (target - now).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    if delta == -1:
        return "Yesterday"
    if delta > 1:
        return f"In {delta} days"
    return f"{abs(delta)} days ago"


def _started_ago(start: date | None, *, now: date) -> str | None:
    if not start:
        return None
    days = (now - start).days
    if days < 0:
        return "Starts soon"
    if days == 0:
        return "Started today"
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = max(days // 30, 1)
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = months // 12
    return f"{years} year{'s' if years != 1 else ''} ago"


def _format_inr(amount: float) -> str:
    if amount == int(amount):
        return f"₹{amount:,.0f}"
    return f"₹{amount:,.2f}"


def _serialize_gift(gift: RecurringGift, program: Program | None, *, today: date) -> dict[str, Any]:
    amount = _as_float(gift.amount)
    freq = _frequency_meta(gift.frequency)
    cat = _normalize_category(program.category if program else None)
    status = _status_label(gift.status)
    start = gift.start_date
    next_pay = gift.next_payment_date if status == "Active" else gift.next_payment_date
    paid_count = int(gift.payments_made or 0)
    contributed = round(amount * paid_count, 2)
    monthly = _monthly_equivalent(amount, gift.frequency)

    return {
        "id": f"rg-{gift.gift_id}",
        "gift_id": gift.gift_id,
        "title": program.program_name if program else "General Support",
        "ngo_name": gift.organization_name or "Aja Abayahastham",
        "category": cat,
        "amount": amount,
        "amount_label": f"{_format_inr(amount)} / {freq['short']}",
        "frequency": freq["id"],
        "frequency_label": freq["label"],
        "monthly_equivalent": monthly,
        "start_date": start.isoformat() if start else None,
        "start_label": start.strftime("%d %b %Y") if start else "—",
        "start_relative": _started_ago(start, now=today),
        "next_payment_date": next_pay.isoformat() if next_pay else None,
        "next_payment_label": next_pay.strftime("%d %b %Y") if next_pay else None,
        "next_payment_relative": _relative_to_now(next_pay, now=today) if next_pay else None,
        "payments_made": paid_count,
        "contributed": contributed,
        "status": status,
        "raw_status": gift.status,
        "payment_method": gift.payment_method,
        "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
        "can_edit": status in {"Active", "Paused"},
        "can_pause": status == "Active",
        "can_resume": status == "Paused",
        "can_cancel": status in {"Active", "Paused"},
        "can_view": True,
    }


def _in_period(start: date | None, period: str, now: datetime) -> bool:
    if not start:
        return True
    key = (period or "all").lower().replace("-", "_")
    if key in {"all", "all_time"}:
        return True
    cur_start, cur_end, _, _ = _period_bounds(period, now)
    dt = datetime.combine(start, datetime.min.time())
    return cur_start <= dt < cur_end


def _sort_rows(rows: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    key = (sort or "next_payment").lower().replace("-", "_")
    if key == "amount":
        return sorted(rows, key=lambda r: (-_as_float(r.get("amount")), r.get("gift_id") or 0))
    if key in {"start_date", "start"}:
        return sorted(rows, key=lambda r: (r.get("start_date") or "", r.get("gift_id") or 0), reverse=True)
    if key == "status":
        return sorted(rows, key=lambda r: (r.get("status") or "", r.get("gift_id") or 0))
    return sorted(
        rows,
        key=lambda r: (
            r.get("next_payment_date") is None,
            r.get("next_payment_date") or "9999-12-31",
            r.get("gift_id") or 0,
        ),
    )


def _compute_impact(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_paid = sum(_as_float(r.get("contributed")) for r in rows if r.get("status") != "Cancelled")
    causes = {r.get("category") for r in rows if r.get("category") and r.get("status") != "Cancelled"}
    lives = int(total_paid // RUPEES_PER_LIFE) if total_paid > 0 else 0

    by_cat: dict[str, float] = {}
    for row in rows:
        if row.get("status") != "Active":
            continue
        cat = row.get("category") or "Others"
        by_cat[cat] = by_cat.get(cat, 0.0) + _as_float(row.get("monthly_equivalent"))
    monthly_total = round(sum(by_cat.values()), 2)
    breakdown = []
    for name, amount in sorted(by_cat.items(), key=lambda x: -x[1]):
        pct = round((amount / monthly_total) * 100, 1) if monthly_total else 0.0
        breakdown.append(
            {
                "name": name,
                "amount": round(amount, 2),
                "percent": pct,
                "color": CATEGORY_COLORS.get(name, CATEGORY_COLORS["Others"]),
            }
        )
    return {
        "lives_impacted": lives if total_paid > 0 else None,
        "causes_supported": len(causes),
        "by_category": breakdown,
        "monthly_total": monthly_total,
    }


async def _load_pairs(db: AsyncSession, donor_id: int) -> list[tuple[RecurringGift, Program | None]]:
    result = await db.execute(
        select(RecurringGift, Program)
        .join(Program, Program.program_id == RecurringGift.program_id, isouter=True)
        .where(RecurringGift.donor_id == donor_id)
        .order_by(RecurringGift.start_date.desc(), RecurringGift.gift_id.desc())
    )
    return list(result.all())


def _empty_payload(
    *,
    period: str,
    tab: str,
    category: str | None,
    sort: str,
    page: int,
    page_size: int,
    has_profile: bool = False,
) -> dict[str, Any]:
    return {
        "has_profile": has_profile,
        "empty": True,
        "period": period,
        "tab": tab,
        "category": category or "all",
        "sort": sort or "next_payment",
        "page": page,
        "page_size": page_size,
        "total": 0,
        "total_pages": 0,
        "categories": [],
        "summary": _empty_summary(),
        "impact": _empty_impact(),
        "upcoming_payments": [],
        "items": [],
        "meta": {
            "frequencies": FREQUENCY_META,
            "payment_methods": list(PAYMENT_METHODS),
            "sort_options": [
                {"id": "next_payment", "label": "Next Payment"},
                {"id": "amount", "label": "Amount"},
                {"id": "start_date", "label": "Start Date"},
                {"id": "status", "label": "Status"},
            ],
        },
    }


async def build_my_recurring_gifts(
    db: AsyncSession,
    *,
    user_id: int,
    period: str = "all",
    tab: str = "all",
    category: str | None = None,
    sort: str = "next_payment",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    await ensure_recurring_gifts_table(db)
    profile = await _resolve_donor(db, user_id)
    if not profile:
        return _empty_payload(
            period=period, tab=tab, category=category, sort=sort, page=page, page_size=page_size
        )

    pairs = await _load_pairs(db, profile.donor_id)
    today = date.today()
    now = datetime.utcnow()
    all_rows = [_serialize_gift(g, prog, today=today) for g, prog in pairs]

    active = [r for r in all_rows if r["status"] == "Active"]
    upcoming_candidates = [r for r in active if r.get("next_payment_date")]
    upcoming_candidates = sorted(upcoming_candidates, key=lambda r: r["next_payment_date"])
    next_up = upcoming_candidates[0] if upcoming_candidates else None
    total_contributed = round(sum(_as_float(r.get("contributed")) for r in all_rows), 2)
    donations_count = sum(int(r.get("payments_made") or 0) for r in all_rows)
    monthly_commitment = round(sum(_as_float(r.get("monthly_equivalent")) for r in active), 2)
    impact = _compute_impact(all_rows)
    causes = {r["category"] for r in all_rows if r.get("category")}

    summary = {
        "active_count": len(active),
        "monthly_commitment": monthly_commitment,
        "total_contributed": total_contributed,
        "donations_count": donations_count,
        "next_payment_date": next_up["next_payment_date"] if next_up else None,
        "next_payment_label": next_up["next_payment_label"] if next_up else None,
        "next_payment_amount": next_up["amount"] if next_up else 0.0,
        "lives_impacted": impact["lives_impacted"],
        "causes_supported": impact["causes_supported"] or len(causes),
    }

    upcoming_payments = []
    for row in upcoming_candidates[:6]:
        nd = row.get("next_payment_date")
        day_label = "—"
        mon_label = ""
        if nd:
            d = date.fromisoformat(nd)
            day_label = f"{d.day:02d}"
            mon_label = month_abbr[d.month].upper()
        upcoming_payments.append(
            {
                "id": row["id"],
                "gift_id": row["gift_id"],
                "title": row["title"],
                "ngo_name": row["ngo_name"],
                "amount": row["amount"],
                "frequency_label": row["frequency_label"],
                "date": nd,
                "day_label": day_label,
                "month_label": mon_label,
            }
        )

    tab_key = (tab or "all").lower().replace("-", "_")
    rows = list(all_rows)
    if tab_key in {"active", "active_gifts"}:
        rows = [r for r in rows if r["status"] == "Active"]
    elif tab_key in {"paused"}:
        rows = [r for r in rows if r["status"] == "Paused"]
    elif tab_key in {"cancelled", "canceled"}:
        rows = [r for r in rows if r["status"] == "Cancelled"]
    elif tab_key in {"completed"}:
        rows = [r for r in rows if r["status"] == "Completed"]

    rows = [
        r
        for r in rows
        if _in_period(
            date.fromisoformat(r["start_date"]) if r.get("start_date") else None,
            period,
            now,
        )
    ]

    categories = sorted({r["category"] for r in all_rows if r.get("category")})
    cat_filter = (category or "").strip()
    if cat_filter and cat_filter.lower() not in {"all", "all causes", "all_causes"}:
        rows = [r for r in rows if (r.get("category") or "").lower() == cat_filter.lower()]

    rows = _sort_rows(rows, sort)

    total = len(rows)
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    total_pages = (total + page_size - 1) // page_size if total else 0
    start = (page - 1) * page_size
    page_items = rows[start : start + page_size]

    return {
        "has_profile": True,
        "empty": len(all_rows) == 0,
        "period": period,
        "tab": tab,
        "category": cat_filter or "all",
        "sort": sort or "next_payment",
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "categories": categories,
        "summary": summary,
        "impact": impact,
        "upcoming_payments": upcoming_payments,
        "items": page_items,
        "profile": {
            "donor_id": profile.donor_id,
            "full_name": profile.full_name,
            "email": profile.email,
        },
        "meta": {
            "frequencies": FREQUENCY_META,
            "payment_methods": list(PAYMENT_METHODS),
            "sort_options": [
                {"id": "next_payment", "label": "Next Payment"},
                {"id": "amount", "label": "Amount"},
                {"id": "start_date", "label": "Start Date"},
                {"id": "status", "label": "Status"},
            ],
        },
    }


async def count_active_recurring_gifts(db: AsyncSession, *, donor_id: int) -> int:
    await ensure_recurring_gifts_table(db)
    result = await db.execute(
        select(RecurringGift).where(
            RecurringGift.donor_id == donor_id,
            RecurringGift.status.in_(tuple(ACTIVE)),
        )
    )
    return len(list(result.scalars().all()))


async def list_recurring_gifts_for_donations(
    db: AsyncSession, *, donor_id: int
) -> list[dict[str, Any]]:
    await ensure_recurring_gifts_table(db)
    pairs = await _load_pairs(db, donor_id)
    today = date.today()
    rows = []
    for gift, program in pairs:
        item = _serialize_gift(gift, program, today=today)
        dt_label = item.get("next_payment_label") or item.get("start_label")
        rows.append(
            {
                "id": item["id"],
                "donation_id": item["gift_id"],
                "type": "MONEY",
                "donation_kind": "recurring",
                "title": item["title"],
                "ngo_name": item["ngo_name"],
                "category": item["category"],
                "date": item.get("next_payment_date") or item.get("start_date"),
                "date_label": dt_label or "—",
                "time_label": item.get("frequency_label"),
                "amount": item["amount"],
                "quantity": None,
                "status": item["status"],
                "raw_status": item["raw_status"],
                "payment_method": item.get("payment_method"),
                "receipt_available": False,
                "image_url": item["image_url"],
                "sort_at": item.get("next_payment_date") or item.get("start_date") or "",
            }
        )
    return rows


async def _get_owned_gift(
    db: AsyncSession, *, user_id: int, gift_id: int
) -> tuple[DonorProfile, RecurringGift]:
    await ensure_recurring_gifts_table(db)
    profile = await _resolve_donor(db, user_id)
    if not profile:
        raise LookupError("Donor profile not found")
    result = await db.execute(
        select(RecurringGift).where(
            RecurringGift.gift_id == gift_id,
            RecurringGift.donor_id == profile.donor_id,
        )
    )
    gift = result.scalar_one_or_none()
    if not gift:
        raise LookupError("Recurring gift not found")
    return profile, gift


async def update_recurring_gift(
    db: AsyncSession,
    *,
    user_id: int,
    gift_id: int,
    amount: float | None = None,
    frequency: str | None = None,
    payment_method: str | None = None,
    next_payment_date: date | None = None,
) -> dict[str, Any]:
    _, gift = await _get_owned_gift(db, user_id=user_id, gift_id=gift_id)
    status = _status_label(gift.status)
    if status not in {"Active", "Paused"}:
        raise ValueError("Only active or paused gifts can be edited")

    if amount is not None:
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        gift.amount = round(float(amount), 2)

    if frequency is not None:
        freq = frequency.strip().upper()
        if freq not in FREQUENCIES:
            raise ValueError("Unsupported frequency")
        gift.frequency = freq

    if payment_method is not None:
        method = payment_method.strip()
        gift.payment_method = method or None

    if next_payment_date is not None:
        if status != "Active":
            raise ValueError("Next payment date can only be changed for active gifts")
        if next_payment_date < date.today():
            raise ValueError("Next payment date cannot be in the past")
        gift.next_payment_date = next_payment_date

    gift.updated_at = datetime.utcnow()
    await db.commit()
    return {"ok": True, "gift_id": gift.gift_id, "status": _status_label(gift.status)}


async def pause_recurring_gift(db: AsyncSession, *, user_id: int, gift_id: int) -> dict[str, Any]:
    _, gift = await _get_owned_gift(db, user_id=user_id, gift_id=gift_id)
    if _status_label(gift.status) != "Active":
        raise ValueError("Only active gifts can be paused")
    gift.status = "PAUSED"
    gift.paused_at = datetime.utcnow()
    gift.next_payment_date = None
    gift.updated_at = datetime.utcnow()
    await db.commit()
    return {"ok": True, "gift_id": gift.gift_id, "status": "Paused"}


async def resume_recurring_gift(db: AsyncSession, *, user_id: int, gift_id: int) -> dict[str, Any]:
    _, gift = await _get_owned_gift(db, user_id=user_id, gift_id=gift_id)
    if _status_label(gift.status) != "Paused":
        raise ValueError("Only paused gifts can be resumed")
    gift.status = "ACTIVE"
    gift.paused_at = None
    gift.next_payment_date = next_date_from(date.today(), gift.frequency)
    gift.updated_at = datetime.utcnow()
    await db.commit()
    return {
        "ok": True,
        "gift_id": gift.gift_id,
        "status": "Active",
        "next_payment_date": gift.next_payment_date.isoformat() if gift.next_payment_date else None,
    }


async def cancel_recurring_gift(db: AsyncSession, *, user_id: int, gift_id: int) -> dict[str, Any]:
    _, gift = await _get_owned_gift(db, user_id=user_id, gift_id=gift_id)
    if _status_label(gift.status) not in {"Active", "Paused"}:
        raise ValueError("This gift cannot be cancelled")
    gift.status = "CANCELLED"
    gift.cancelled_at = datetime.utcnow()
    gift.next_payment_date = None
    gift.updated_at = datetime.utcnow()
    await db.commit()
    return {"ok": True, "gift_id": gift.gift_id, "status": "Cancelled"}
