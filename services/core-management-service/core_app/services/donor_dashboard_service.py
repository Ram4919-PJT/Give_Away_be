"""Server-side aggregations for the authenticated donor dashboard."""

from __future__ import annotations

from calendar import month_abbr
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.donations import ItemDonation, MoneyDonation
from core_app.models.profiles import DonorProfile, Program

# ₹500 confirmed contribution ≈ 1 life impacted (documented business rule).
RUPEES_PER_LIFE = 500
MILESTONE_TARGETS = (5_000, 10_000, 25_000, 30_000, 50_000, 100_000, 250_000, 500_000)
STREAK_WEEKS = 12

CONFIRMED_MONEY = {"CONFIRMED", "COMPLETED", "SUCCESS", "PAID"}
PENDING_MONEY = {"INITIATED", "PAYMENT_PENDING", "PENDING", "PROCESSING"}
FAILED_MONEY = {"FAILED", "FAILURE"}
REFUNDED_MONEY = {"REFUNDED", "REFUND"}
CANCELLED_MONEY = {"CANCELLED", "CANCELED"}

CATEGORY_COLORS = {
    "Education": "#1268E8",
    "Medical": "#20B878",
    "Healthcare": "#20B878",
    "Relief": "#F97316",
    "Food & Shelter": "#F97316",
    "Infrastructure": "#A855F7",
    "Environment": "#A855F7",
    "Sanitation": "#A855F7",
    "Vocational": "#0EA5E9",
    "Disability": "#6366F1",
    "Others": "#94A3B8",
}

CATEGORY_IMAGES = {
    "Education": "/assets/donor/Education_for_All.png",
    "Medical": "/assets/donor/Healthcare_Support.png",
    "Healthcare": "/assets/donor/Healthcare_Support.png",
    "Relief": "/assets/donor/Food_for_Hunger.png",
    "Food & Shelter": "/assets/donor/Food_for_Hunger.png",
    "Infrastructure": "/assets/donor/Save_Environment.png",
    "Environment": "/assets/donor/Save_Environment.png",
    "Sanitation": "/assets/donor/Save_Environment.png",
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
        return value if value.tzinfo is None else value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _normalize_category(raw: str | None) -> str:
    if not raw:
        return "Others"
    key = raw.strip()
    aliases = {
        "Medical": "Healthcare",
        "Health": "Healthcare",
        "Relief": "Food & Shelter",
        "Food": "Food & Shelter",
        "Clothing": "Food & Shelter",
        "Food Packs": "Food & Shelter",
        "Infrastructure": "Environment",
        "Sanitation": "Environment",
        "Clean Water": "Environment",
    }
    return aliases.get(key, key)


def _money_status_label(status: str | None) -> str:
    s = (status or "").upper()
    if s in CONFIRMED_MONEY:
        return "Completed"
    if s in FAILED_MONEY:
        return "Failed"
    if s in REFUNDED_MONEY:
        return "Refunded"
    if s in CANCELLED_MONEY:
        return "Cancelled"
    if s in PENDING_MONEY:
        return "Pending"
    return "Pending"


def _item_status_label(status: str | None) -> str:
    s = (status or "").upper()
    if s in {"RECEIVED", "DELIVERED", "COMPLETED", "DISTRIBUTED"}:
        return "Completed"
    if s in {"CANCELLED", "CANCELED", "REJECTED"}:
        return "Cancelled"
    if s in {"FAILED"}:
        return "Failed"
    return "Pending"


def _period_bounds(period: str, now: datetime) -> tuple[datetime, datetime, datetime, datetime]:
    """Return (current_start, current_end, previous_start, previous_end)."""
    end = now
    p = (period or "year").lower().replace(" ", "_").replace("-", "_")

    if p in {"month", "this_month"}:
        start = datetime(now.year, now.month, 1)
        if now.month == 1:
            prev_start = datetime(now.year - 1, 12, 1)
            prev_end = start
        else:
            prev_start = datetime(now.year, now.month - 1, 1)
            prev_end = start
        return start, end, prev_start, prev_end

    if p in {"last_month"}:
        if now.month == 1:
            start = datetime(now.year - 1, 12, 1)
            end = datetime(now.year, 1, 1)
            prev_start = datetime(now.year - 1, 11, 1)
        else:
            start = datetime(now.year, now.month - 1, 1)
            end = datetime(now.year, now.month, 1)
            if now.month == 2:
                prev_start = datetime(now.year, 1, 1)
            else:
                prev_start = datetime(now.year, now.month - 2, 1)
        return start, end, prev_start, start

    if p in {"last_year"}:
        start = datetime(now.year - 1, 1, 1)
        end = datetime(now.year, 1, 1)
        prev_start = datetime(now.year - 2, 1, 1)
        return start, end, prev_start, start

    # default: this year
    start = datetime(now.year, 1, 1)
    prev_start = datetime(now.year - 1, 1, 1)
    prev_end = start
    return start, end, prev_start, prev_end


def _growth_pct(current: float, previous: float) -> float:
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _iso_week_key(dt: datetime) -> tuple[int, int]:
    iso = dt.isocalendar()
    return iso.year, iso.week


def _compute_milestone(total: float) -> dict[str, Any]:
    target = MILESTONE_TARGETS[-1]
    for t in MILESTONE_TARGETS:
        if total < t:
            target = t
            break
    remaining = max(target - total, 0)
    progress = 0.0 if target <= 0 else min(round((total / target) * 100, 1), 100.0)
    return {
        "current": round(total, 2),
        "target": target,
        "remaining": round(remaining, 2),
        "progress_pct": progress,
        "reward_label": "Certificate of Impact",
        "message": (
            f"You're just ₹{remaining:,.0f} away from your next milestone!"
            if remaining > 0
            else "You've reached your current milestone. Amazing work!"
        ),
    }


def _compute_streak(donation_dates: list[datetime], weeks: int = STREAK_WEEKS) -> dict[str, Any]:
    if not donation_dates:
        return {
            "weeks": 0,
            "active_weeks": [False] * weeks,
            "message": "Start your giving journey",
        }

    week_set = {_iso_week_key(d) for d in donation_dates if d}
    today = datetime.utcnow()
    active: list[bool] = []
    # oldest → newest across the last N weeks
    for i in range(weeks - 1, -1, -1):
        ref = today - timedelta(weeks=i)
        active.append(_iso_week_key(ref) in week_set)

    streak = 0
    for flag in reversed(active):
        if flag:
            streak += 1
        else:
            break

    return {
        "weeks": streak,
        "active_weeks": active,
        "message": (
            "Keep it up! Your consistency inspires change."
            if streak > 0
            else "Start your giving journey"
        ),
    }


async def build_donor_dashboard(
    db: AsyncSession,
    *,
    user_id: int,
    period: str = "year",
) -> dict[str, Any]:
    profile_res = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    profile = profile_res.scalar_one_or_none()
    if not profile:
        return {
            "profile": None,
            "has_profile": False,
            "empty": True,
            "stats": _empty_stats(),
            "series": [],
            "cause_breakdown": [],
            "top_causes": [],
            "recent_donations": [],
            "milestone": _compute_milestone(0),
            "giving_streak": _compute_streak([]),
            "period": period,
        }

    donor_id = profile.donor_id
    money_res = await db.execute(
        select(MoneyDonation, Program)
        .join(Program, Program.program_id == MoneyDonation.program_id, isouter=True)
        .where(MoneyDonation.donor_id == donor_id)
        .order_by(MoneyDonation.donated_at.desc())
    )
    money_rows = money_res.all()

    item_res = await db.execute(
        select(ItemDonation)
        .where(ItemDonation.donor_id == donor_id)
        .order_by(ItemDonation.item_donation_id.desc())
    )
    item_rows = list(item_res.scalars().all())

    now = datetime.utcnow()
    cur_start, cur_end, prev_start, prev_end = _period_bounds(period, now)

    confirmed_money: list[tuple[MoneyDonation, Program | None, datetime]] = []
    all_money_events: list[tuple[MoneyDonation, Program | None, datetime]] = []

    for donation, program in money_rows:
        dt = _as_dt(donation.donated_at) or now
        all_money_events.append((donation, program, dt))
        if (donation.payment_status or "").upper() in CONFIRMED_MONEY:
            confirmed_money.append((donation, program, dt))

    total_confirmed = sum(_as_float(d.amount) for d, _, _ in confirmed_money)
    period_total = sum(
        _as_float(d.amount) for d, _, dt in confirmed_money if cur_start <= dt < cur_end
    )
    prev_period_total = sum(
        _as_float(d.amount) for d, _, dt in confirmed_money if prev_start <= dt < prev_end
    )

    # Lives: ₹ rule + received item quantities
    lives = int(total_confirmed // RUPEES_PER_LIFE)
    lives += sum(
        int(item.quantity or 0)
        for item in item_rows
        if (item.status or "").upper() in {"RECEIVED", "DELIVERED", "COMPLETED", "DISTRIBUTED"}
    )

    # Programs / causes / NGOs proxy (programs are the partnered cause vehicles)
    distinct_program_ids = {d.program_id for d, _, _ in confirmed_money}
    categories = {
        _normalize_category(program.category if program else None)
        for _, program, _ in confirmed_money
    }
    categories |= {
        _normalize_category(item.category) for item in item_rows if item.category
    }
    causes_supported = len(categories)
    ngos_supported = len(distinct_program_ids) or (1 if item_rows else 0)

    # Years of giving from earliest donation
    earliest: datetime | None = None
    for _, _, dt in confirmed_money:
        if earliest is None or dt < earliest:
            earliest = dt
    for item in item_rows:
        # item donations lack donated_at — use id order as weak signal; skip for years
        pass
    if earliest:
        years = max((now - earliest).days / 365.25, 0.1)
        years_of_giving = round(years, 1)
    else:
        years_of_giving = 0.0

    # Growth metrics (period vs previous period)
    donation_growth = _growth_pct(period_total, prev_period_total)

    prev_lives_proxy = int(prev_period_total // RUPEES_PER_LIFE)
    cur_lives_proxy = int(period_total // RUPEES_PER_LIFE)
    impact_growth = _growth_pct(cur_lives_proxy, prev_lives_proxy)

    prev_programs = {
        d.program_id for d, _, dt in confirmed_money if prev_start <= dt < prev_end
    }
    cur_programs = {
        d.program_id for d, _, dt in confirmed_money if cur_start <= dt < cur_end
    }
    ngo_growth = _growth_pct(float(len(cur_programs)), float(len(prev_programs)))

    # Monthly series for selected period (or last 6 months for year views)
    series = _build_series(confirmed_money, period, now, cur_start, cur_end)

    # Cause breakdown (all-time confirmed; filtered to period amounts when possible)
    cause_amounts: dict[str, float] = defaultdict(float)
    for donation, program, dt in confirmed_money:
        if not (cur_start <= dt < cur_end):
            # For all-time top causes still show lifetime; breakdown uses period
            continue
        cat = _normalize_category(program.category if program else None)
        cause_amounts[cat] += _as_float(donation.amount)

    # If period has no confirmed donations, fall back to all-time for charts
    if not cause_amounts:
        for donation, program, _ in confirmed_money:
            cat = _normalize_category(program.category if program else None)
            cause_amounts[cat] += _as_float(donation.amount)

    breakdown_total = sum(cause_amounts.values()) or 1.0
    cause_breakdown = []
    for name, amount in sorted(cause_amounts.items(), key=lambda x: x[1], reverse=True):
        cause_breakdown.append(
            {
                "name": name,
                "amount": round(amount, 2),
                "percent": round((amount / breakdown_total) * 100, 1),
                "color": CATEGORY_COLORS.get(name, CATEGORY_COLORS["Others"]),
                "image_url": CATEGORY_IMAGES.get(name, CATEGORY_IMAGES["Education"]),
            }
        )

    top_causes = cause_breakdown[:5]

    recent = _build_recent(all_money_events, item_rows, limit=5)

    streak_dates = [dt for _, _, dt in confirmed_money]
    donations_count = len(confirmed_money) + len(
        [i for i in item_rows if (i.status or "").upper() in {"RECEIVED", "DELIVERED", "COMPLETED"}]
    )

    empty = total_confirmed <= 0 and not item_rows

    return {
        "has_profile": True,
        "empty": empty,
        "period": period,
        "profile": {
            "donor_id": profile.donor_id,
            "user_id": profile.user_id,
            "full_name": profile.full_name,
            "email": profile.email,
            "mobile": profile.mobile,
            "avatar_url": "/assets/donor/Donor_Profile_Avatar.png",
        },
        "stats": {
            "total_donated": round(total_confirmed, 2),
            "period_total": round(period_total, 2),
            "lives_impacted": lives,
            "ngos_supported": ngos_supported,
            "causes_supported": causes_supported,
            "years_of_giving": years_of_giving,
            "donations_count": donations_count,
            "donation_growth_pct": donation_growth,
            "impact_growth_pct": impact_growth,
            "ngo_growth_pct": ngo_growth,
            "items_donated": len(item_rows),
        },
        "series": series,
        "cause_breakdown": cause_breakdown,
        "top_causes": top_causes,
        "recent_donations": recent,
        "milestone": _compute_milestone(total_confirmed),
        "giving_streak": _compute_streak(streak_dates),
        "impact_snapshot": {
            "lives_impacted": lives,
            "donations_made": donations_count,
            "ngos_supported": ngos_supported,
        },
    }


def _empty_stats() -> dict[str, Any]:
    return {
        "total_donated": 0,
        "period_total": 0,
        "lives_impacted": 0,
        "ngos_supported": 0,
        "causes_supported": 0,
        "years_of_giving": 0,
        "donations_count": 0,
        "donation_growth_pct": 0,
        "impact_growth_pct": 0,
        "ngo_growth_pct": 0,
        "items_donated": 0,
    }


def _build_series(
    confirmed_money: list[tuple[MoneyDonation, Program | None, datetime]],
    period: str,
    now: datetime,
    cur_start: datetime,
    cur_end: datetime,
) -> list[dict[str, Any]]:
    p = (period or "year").lower().replace("-", "_")
    buckets: dict[str, float] = {}
    order: list[str] = []

    if p in {"month", "this_month", "last_month"}:
        # weekly buckets inside the period
        cursor = cur_start.date()
        end_d = min(cur_end.date(), now.date() + timedelta(days=1))
        week_i = 1
        while cursor < end_d:
            label = cursor.strftime("%b %d")
            order.append(label)
            buckets[label] = 0.0
            cursor += timedelta(days=7)
            week_i += 1
            if week_i > 6:
                break
        for donation, _, dt in confirmed_money:
            if not (cur_start <= dt < cur_end):
                continue
            # assign to nearest bucket start
            assigned = order[0] if order else dt.strftime("%b %d")
            for label in order:
                try:
                    bucket_date = datetime.strptime(f"{label} {dt.year}", "%b %d %Y")
                except ValueError:
                    continue
                if dt.date() >= bucket_date.date():
                    assigned = label
            buckets[assigned] = buckets.get(assigned, 0.0) + _as_float(donation.amount)
    else:
        # monthly buckets Jan–current (or full last year)
        if p == "last_year":
            months = list(range(1, 13))
            year = now.year - 1
        else:
            months = list(range(1, (now.month if cur_end.year == now.year else 12) + 1))
            year = cur_start.year
        for m in months:
            label = month_abbr[m]
            order.append(label)
            buckets[label] = 0.0
        for donation, _, dt in confirmed_money:
            if dt.year != year:
                continue
            label = month_abbr[dt.month]
            if label in buckets:
                buckets[label] += _as_float(donation.amount)

    return [{"label": label, "amount": round(buckets.get(label, 0.0), 2)} for label in order]


def _build_recent(
    money_events: list[tuple[MoneyDonation, Program | None, datetime]],
    item_rows: list[ItemDonation],
    limit: int = 5,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for donation, program, dt in money_events:
        cat = _normalize_category(program.category if program else None)
        rows.append(
            {
                "id": f"money-{donation.donation_id}",
                "donation_id": donation.donation_id,
                "type": "MONEY",
                "title": program.program_name if program else "General Support",
                "ngo_name": "Aja Abayahastham",
                "category": cat,
                "date": dt.date().isoformat(),
                "date_label": dt.strftime("%b %d, %Y"),
                "amount": round(_as_float(donation.amount), 2),
                "status": _money_status_label(donation.payment_status),
                "raw_status": donation.payment_status,
                "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
            }
        )

    for item in item_rows:
        cat = _normalize_category(item.category)
        rows.append(
            {
                "id": f"item-{item.item_donation_id}",
                "donation_id": item.item_donation_id,
                "type": "ITEM",
                "title": item.category or "Item Donation",
                "ngo_name": "Aja Abayahastham",
                "category": cat,
                "date": None,
                "date_label": "Recently",
                "amount": None,
                "quantity": item.quantity,
                "status": _item_status_label(item.status),
                "raw_status": item.status,
                "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
            }
        )

    money = [r for r in rows if r.get("type") == "MONEY"]
    items = [r for r in rows if r.get("type") != "MONEY"]
    money.sort(key=lambda r: r.get("date") or "", reverse=True)
    return (money + items)[:limit]
