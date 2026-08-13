"""Authenticated donor impact report: summary, charts, highlights, journey, download."""

from __future__ import annotations

from calendar import month_abbr
from collections import defaultdict
from datetime import date, datetime, timedelta
from html import escape
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.donations import ItemDonation, MoneyDonation
from core_app.models.pledges import DonorPledge
from core_app.models.profiles import DonorProfile, Program
from core_app.models.recurring_gifts import RecurringGift
from core_app.services.donor_dashboard_service import (
    CATEGORY_COLORS,
    CATEGORY_IMAGES,
    CONFIRMED_MONEY,
    RUPEES_PER_LIFE,
    _as_dt,
    _as_float,
    _growth_pct,
    _normalize_category,
    _period_bounds,
)
from core_app.services.donor_donations_service import ORG_NAME, ORG_TAGLINE
from core_app.services.donor_recurring_gifts_service import ensure_recurring_gifts_table

# Documented conversion rules (same family as donor pledges impact).
RUPEES_PER_CHILD = 1000
RUPEES_PER_PATIENT = 1500
RUPEES_PER_TREE = 50
CHANGE_MAKER_AMOUNT = 5_000
COMPLETED_ITEMS = {"RECEIVED", "DELIVERED", "COMPLETED", "DISTRIBUTED"}


def _empty_summary() -> dict[str, Any]:
    return {
        "lives_impacted": 0,
        "donations_count": 0,
        "total_donated": 0.0,
        "causes_supported": 0,
        "ngos_supported": 0,
        "lives_growth_pct": None,
        "donations_growth_pct": None,
        "amount_growth_pct": None,
        "causes_growth_pct": None,
        "ngos_growth_pct": None,
    }


async def _resolve_donor(db: AsyncSession, user_id: int) -> DonorProfile | None:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    return result.scalar_one_or_none()


def _period_window(period: str, now: datetime) -> tuple[datetime, datetime, datetime, datetime]:
    key = (period or "year").lower().replace("-", "_")
    if key in {"all", "all_time"}:
        start = datetime(1970, 1, 1)
        prev_start = datetime(now.year - 1, 1, 1)
        prev_end = datetime(now.year, 1, 1)
        return start, now, prev_start, prev_end
    return _period_bounds(period, now)


def _optional_growth(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return _growth_pct(current, previous)


def _lives_from_amount(amount: float) -> int:
    return int(max(amount, 0) // RUPEES_PER_LIFE)


def _in_window(dt: datetime | None, start: datetime, end: datetime) -> bool:
    if dt is None:
        return False
    return start <= dt < end


def _build_lives_series(
    dated_amounts: list[tuple[datetime, float]],
    period: str,
    now: datetime,
    cur_start: datetime,
    cur_end: datetime,
) -> list[dict[str, Any]]:
    key = (period or "year").lower().replace("-", "_")
    buckets: dict[str, float] = {}
    order: list[str] = []

    if key in {"month", "this_month", "last_month"}:
        cursor = cur_start.date()
        end_d = min(cur_end.date(), now.date() + timedelta(days=1))
        week_i = 1
        while cursor < end_d and week_i <= 6:
            label = cursor.strftime("%b %d")
            order.append(label)
            buckets[label] = 0.0
            cursor += timedelta(days=7)
            week_i += 1
        for dt, amount in dated_amounts:
            if not _in_window(dt, cur_start, cur_end):
                continue
            assigned = order[0] if order else dt.strftime("%b %d")
            for label in order:
                try:
                    bucket_date = datetime.strptime(f"{label} {dt.year}", "%b %d %Y")
                except ValueError:
                    continue
                if dt.date() >= bucket_date.date():
                    assigned = label
            buckets[assigned] = buckets.get(assigned, 0.0) + amount
    else:
        if key == "last_year":
            months = list(range(1, 13))
            year = now.year - 1
        elif key in {"all", "all_time"}:
            years = sorted({dt.year for dt, _ in dated_amounts}) or [now.year]
            if len(years) == 1:
                months = list(range(1, (now.month if years[0] == now.year else 12) + 1))
                year = years[0]
            else:
                order = [str(y) for y in years]
                for y in years:
                    buckets[str(y)] = 0.0
                for dt, amount in dated_amounts:
                    label = str(dt.year)
                    if label in buckets:
                        buckets[label] += amount
                cumulative = 0
                series = []
                for label in order:
                    amt = round(buckets.get(label, 0.0), 2)
                    lives = _lives_from_amount(amt)
                    cumulative += lives
                    series.append(
                        {
                            "label": label,
                            "amount": amt,
                            "lives": lives,
                            "cumulative_lives": cumulative,
                        }
                    )
                return series
        else:
            months = list(range(1, (now.month if cur_end.year == now.year else 12) + 1))
            year = cur_start.year
        for m in months:
            label = month_abbr[m]
            order.append(label)
            buckets[label] = 0.0
        for dt, amount in dated_amounts:
            if dt.year != year:
                continue
            label = month_abbr[dt.month]
            if label in buckets:
                buckets[label] += amount

    cumulative = 0
    series = []
    for label in order:
        amt = round(buckets.get(label, 0.0), 2)
        lives = _lives_from_amount(amt)
        cumulative += lives
        series.append(
            {
                "label": label,
                "amount": amt,
                "lives": lives,
                "cumulative_lives": cumulative,
            }
        )
    return series


def _highlights_from_categories(paid_by_cat: dict[str, float], item_qty_by_cat: dict[str, int]) -> list[dict[str, Any]]:
    children = int(paid_by_cat.get("Education", 0) // RUPEES_PER_CHILD)
    patients = int(
        (paid_by_cat.get("Healthcare", 0) + paid_by_cat.get("Medical", 0)) // RUPEES_PER_PATIENT
    )
    trees = int(
        (
            paid_by_cat.get("Environment", 0)
            + paid_by_cat.get("Sanitation", 0)
            + paid_by_cat.get("Infrastructure", 0)
        )
        // RUPEES_PER_TREE
    )
    relief_items = sum(
        qty
        for cat, qty in item_qty_by_cat.items()
        if cat in {"Food & Shelter", "Relief", "Clothing"}
    )

    candidates = [
        {
            "id": "children",
            "label": "Children Educated",
            "value": children,
            "color": "#1268E8",
            "bg": "#EEF5FF",
        },
        {
            "id": "healthcare",
            "label": "People Received Healthcare",
            "value": patients,
            "color": "#12B76A",
            "bg": "#E8F8F0",
        },
        {
            "id": "meals",
            "label": "Relief Items Provided",
            "value": relief_items,
            "color": "#EA580C",
            "bg": "#FFF7ED",
        },
        {
            "id": "trees",
            "label": "Trees Planted",
            "value": trees,
            "color": "#0F9D8A",
            "bg": "#E7F8F3",
        },
    ]
    return [row for row in candidates if int(row["value"] or 0) > 0]


def _build_journey(
    dated_amounts: list[tuple[datetime, float]],
    donations_count: int,
    total_donated: float,
) -> list[dict[str, Any]]:
    events = sorted(dated_amounts, key=lambda x: x[0])
    milestones: list[dict[str, Any]] = []
    if not events:
        return milestones

    first_dt = events[0][0]
    milestones.append(
        {
            "id": "first",
            "title": "First Donation",
            "date": first_dt.date().isoformat(),
            "date_label": first_dt.strftime("%b %Y"),
            "achieved": True,
        }
    )

    if donations_count >= 10 and len(events) >= 10:
        tenth = events[9][0]
        milestones.append(
            {
                "id": "ten",
                "title": "10 Donations",
                "date": tenth.date().isoformat(),
                "date_label": tenth.strftime("%b %Y"),
                "achieved": True,
            }
        )
    elif donations_count > 0:
        milestones.append(
            {
                "id": "ten",
                "title": "10 Donations",
                "date": None,
                "date_label": f"{donations_count} so far",
                "achieved": False,
            }
        )

    year_mark = first_dt + timedelta(days=365)
    year_done = datetime.utcnow() >= year_mark
    milestones.append(
        {
            "id": "year",
            "title": "1 Year of Giving",
            "date": year_mark.date().isoformat() if year_done else None,
            "date_label": year_mark.strftime("%b %Y") if year_done else "Upcoming",
            "achieved": year_done,
        }
    )

    running = 0.0
    maker_dt = None
    for dt, amount in events:
        running += amount
        if running >= CHANGE_MAKER_AMOUNT:
            maker_dt = dt
            break
    maker_done = maker_dt is not None or total_donated >= CHANGE_MAKER_AMOUNT
    milestones.append(
        {
            "id": "changemaker",
            "title": "Change Maker",
            "date": maker_dt.date().isoformat() if maker_dt else None,
            "date_label": maker_dt.strftime("%b %Y") if maker_dt else ("Achieved" if maker_done else "Keep giving"),
            "achieved": maker_done,
        }
    )
    return milestones


async def build_my_impact(
    db: AsyncSession,
    *,
    user_id: int,
    period: str = "year",
) -> dict[str, Any]:
    await ensure_recurring_gifts_table(db)
    profile = await _resolve_donor(db, user_id)
    if not profile:
        return {
            "has_profile": False,
            "empty": True,
            "period": period,
            "summary": _empty_summary(),
            "series": [],
            "cause_breakdown": [],
            "highlights": [],
            "stories": [],
            "journey": [],
            "download_available": False,
        }

    donor_id = profile.donor_id
    now = datetime.utcnow()
    cur_start, cur_end, prev_start, prev_end = _period_window(period, now)

    money_res = await db.execute(
        select(MoneyDonation, Program)
        .join(Program, Program.program_id == MoneyDonation.program_id, isouter=True)
        .where(MoneyDonation.donor_id == donor_id)
        .order_by(MoneyDonation.donated_at.asc())
    )
    money_rows = money_res.all()

    item_res = await db.execute(
        select(ItemDonation).where(ItemDonation.donor_id == donor_id)
    )
    item_rows = list(item_res.scalars().all())

    pledge_res = await db.execute(
        select(DonorPledge, Program)
        .join(Program, Program.program_id == DonorPledge.program_id, isouter=True)
        .where(DonorPledge.donor_id == donor_id)
    )
    pledge_rows = pledge_res.all()

    gift_res = await db.execute(
        select(RecurringGift, Program)
        .join(Program, Program.program_id == RecurringGift.program_id, isouter=True)
        .where(RecurringGift.donor_id == donor_id)
    )
    gift_rows = gift_res.all()

    confirmed: list[tuple[MoneyDonation, Program | None, datetime]] = []
    for donation, program in money_rows:
        dt = _as_dt(donation.donated_at) or now
        if (donation.payment_status or "").upper() in CONFIRMED_MONEY:
            confirmed.append((donation, program, dt))

    dated_amounts: list[tuple[datetime, float]] = [
        (dt, _as_float(d.amount)) for d, _, dt in confirmed
    ]

    def _money_in(start: datetime, end: datetime) -> tuple[float, int, set[str], set[str]]:
        total = 0.0
        count = 0
        cats: set[str] = set()
        orgs: set[str] = set()
        for donation, program, dt in confirmed:
            if not _in_window(dt, start, end):
                continue
            total += _as_float(donation.amount)
            count += 1
            cats.add(_normalize_category(program.category if program else None))
            orgs.add(ORG_NAME)
        return total, count, cats, orgs

    cur_amount, cur_count, cur_cats, cur_orgs = _money_in(cur_start, cur_end)
    prev_amount, prev_count, prev_cats, prev_orgs = _money_in(prev_start, prev_end)

    lifetime_amount = sum(_as_float(d.amount) for d, _, _ in confirmed)
    lifetime_count = len(confirmed)

    completed_items = [
        item for item in item_rows if (item.status or "").upper() in COMPLETED_ITEMS
    ]
    item_qty = sum(int(item.quantity or 0) for item in completed_items)
    item_qty_by_cat: dict[str, int] = defaultdict(int)
    for item in completed_items:
        cat = _normalize_category(item.category)
        item_qty_by_cat[cat] += int(item.quantity or 0)
        cur_cats.add(cat)

    pledge_paid_lifetime = 0.0
    gift_paid_lifetime = 0.0
    paid_by_cat: dict[str, float] = defaultdict(float)
    org_names: set[str] = set()
    if confirmed or completed_items:
        org_names.add(ORG_NAME)
    program_stories: dict[int, dict[str, Any]] = {}

    period_by_cat: dict[str, float] = defaultdict(float)
    for donation, program, dt in confirmed:
        cat = _normalize_category(program.category if program else None)
        paid_by_cat[cat] += _as_float(donation.amount)
        if _in_window(dt, cur_start, cur_end):
            period_by_cat[cat] += _as_float(donation.amount)
        if program and program.program_id not in program_stories:
            program_stories[program.program_id] = {
                "id": f"program-{program.program_id}",
                "title": program.program_name,
                "description": (program.description or "").strip(),
                "category": cat,
                "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
            }

    for pledge, program in pledge_rows:
        status = (pledge.status or "").upper()
        if status in {"CANCELLED", "CANCELED"}:
            continue
        paid = _as_float(pledge.monthly_amount) * int(pledge.payments_made or 0)
        pledge_paid_lifetime += paid
        cat = _normalize_category(program.category if program else None)
        paid_by_cat[cat] += paid
        if pledge.organization_name:
            org_names.add(pledge.organization_name)
        if program and program.program_id not in program_stories:
            program_stories[program.program_id] = {
                "id": f"program-{program.program_id}",
                "title": program.program_name,
                "description": (program.description or "").strip(),
                "category": cat,
                "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
            }

    for gift, program in gift_rows:
        status = (gift.status or "").upper()
        if status in {"CANCELLED", "CANCELED"}:
            continue
        paid = _as_float(gift.amount) * int(gift.payments_made or 0)
        gift_paid_lifetime += paid
        cat = _normalize_category(program.category if program else None)
        paid_by_cat[cat] += paid
        if gift.organization_name:
            org_names.add(gift.organization_name)
        if program and program.program_id not in program_stories:
            program_stories[program.program_id] = {
                "id": f"program-{program.program_id}",
                "title": program.program_name,
                "description": (program.description or "").strip(),
                "category": cat,
                "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
            }

    lifetime_total = round(lifetime_amount + pledge_paid_lifetime + gift_paid_lifetime, 2)
    donations_count = lifetime_count + len(completed_items)
    lives = _lives_from_amount(lifetime_total) + item_qty

    period_total = round(cur_amount, 2)
    period_lives = _lives_from_amount(period_total)
    prev_lives = _lives_from_amount(prev_amount)

    all_cats = set(cur_cats)
    for donation, program, _ in confirmed:
        all_cats.add(_normalize_category(program.category if program else None))
    for item in item_rows:
        if item.category:
            all_cats.add(_normalize_category(item.category))

    ngo_count = len(org_names) if org_names else (len({d.program_id for d, _, _ in confirmed}) or 0)

    summary = {
        "lives_impacted": lives,
        "donations_count": donations_count,
        "total_donated": lifetime_total,
        "causes_supported": len(all_cats),
        "ngos_supported": ngo_count,
        "period_total": period_total,
        "period_lives": period_lives,
        "lives_growth_pct": _optional_growth(float(period_lives), float(prev_lives)),
        "donations_growth_pct": _optional_growth(float(cur_count), float(prev_count)),
        "amount_growth_pct": _optional_growth(period_total, prev_amount),
        "causes_growth_pct": _optional_growth(float(len(cur_cats)), float(len(prev_cats))),
        "ngos_growth_pct": _optional_growth(float(len(cur_orgs)), float(len(prev_orgs))),
    }

    series = _build_lives_series(dated_amounts, period, now, cur_start, cur_end)

    breakdown_source = period_by_cat or paid_by_cat
    breakdown_total = sum(breakdown_source.values()) or 1.0
    cause_breakdown = []
    for name, amount in sorted(breakdown_source.items(), key=lambda x: x[1], reverse=True):
        cause_breakdown.append(
            {
                "name": name,
                "amount": round(amount, 2),
                "lives": _lives_from_amount(amount),
                "percent": round((amount / breakdown_total) * 100, 1),
                "color": CATEGORY_COLORS.get(name, CATEGORY_COLORS["Others"]),
                "image_url": CATEGORY_IMAGES.get(name, CATEGORY_IMAGES["Education"]),
            }
        )

    highlights = _highlights_from_categories(dict(breakdown_source), dict(item_qty_by_cat))

    stories = []
    for story in program_stories.values():
        text = story["description"] or f"Your support helped advance {story['title']}."
        stories.append(
            {
                "id": story["id"],
                "title": story["title"],
                "text": text,
                "category": story["category"],
                "image_url": story["image_url"],
            }
        )
    stories = stories[:6]

    journey = _build_journey(dated_amounts, donations_count, lifetime_total)

    empty = lifetime_total <= 0 and not completed_items

    return {
        "has_profile": True,
        "empty": empty,
        "period": period,
        "summary": summary,
        "series": series,
        "cause_breakdown": cause_breakdown,
        "highlights": highlights,
        "stories": stories,
        "journey": journey,
        "download_available": not empty,
        "profile": {
            "donor_id": profile.donor_id,
            "full_name": profile.full_name,
            "email": profile.email,
        },
        "share_text": (
            f"I've contributed ₹{lifetime_total:,.0f} and helped impact "
            f"{lives} lives across {len(all_cats)} causes on Give Away."
            if not empty
            else None
        ),
    }


async def build_impact_report_download(
    db: AsyncSession,
    *,
    user_id: int,
) -> tuple[str, str, str]:
    payload = await build_my_impact(db, user_id=user_id, period="all")
    if not payload.get("has_profile"):
        raise LookupError("Donor profile not found")
    if payload.get("empty"):
        raise LookupError("No impact data to download")

    profile = payload.get("profile") or {}
    summary = payload.get("summary") or {}
    causes = payload.get("cause_breakdown") or []
    highlights = payload.get("highlights") or []
    journey = payload.get("journey") or []

    def e(v: Any) -> str:
        return escape(str(v if v is not None else "—"))

    cause_rows = "".join(
        f"<tr><td>{e(c['name'])}</td><td>₹{e(f'{c['amount']:,.2f}')}</td>"
        f"<td>{e(c['lives'])}</td><td>{e(c['percent'])}%</td></tr>"
        for c in causes
    )
    highlight_html = "".join(
        f"<div><span class='muted'>{e(h['label'])}</span><strong>{e(h['value'])}</strong></div>"
        for h in highlights
    ) or "<p class='muted'>No highlight metrics yet.</p>"
    journey_html = "".join(
        f"<li><strong>{e(m['title'])}</strong> — {e(m.get('date_label') or '—')}</li>"
        for m in journey
        if m.get("achieved")
    )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Impact Report</title>
<style>
body{{font-family:Georgia,serif;color:#0B245B;background:#F4F7FC;margin:0}}
.sheet{{max-width:860px;margin:28px auto;background:#fff;border:1px solid #DCE8FA;border-radius:16px;padding:36px}}
h1{{margin:0;font-size:22px}} .muted{{color:#49638F;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin-top:20px;font-size:13px}}
th,td{{text-align:left;padding:10px 8px;border-bottom:1px solid #E8EEF8}}
th{{color:#49638F;font-size:11px;text-transform:uppercase}}
.kpi{{display:flex;gap:18px;flex-wrap:wrap;margin-top:18px}}
.kpi div{{background:#F7FAFF;border:1px solid #DCE8FA;border-radius:12px;padding:12px 14px;min-width:140px}}
.kpi strong{{display:block;font-size:18px;margin-top:4px}}
ul{{padding-left:18px}}
</style></head><body><div class="sheet">
<h1>{e(ORG_NAME)} — Impact Report</h1>
<p class="muted">{e(ORG_TAGLINE)} · Prepared for {e(profile.get('full_name'))}</p>
<div class="kpi">
  <div><span class="muted">Lives Impacted</span><strong>{e(summary.get('lives_impacted', 0))}</strong></div>
  <div><span class="muted">Donations</span><strong>{e(summary.get('donations_count', 0))}</strong></div>
  <div><span class="muted">Total Donated</span><strong>₹{e(f"{summary.get('total_donated', 0):,.2f}")}</strong></div>
  <div><span class="muted">Causes</span><strong>{e(summary.get('causes_supported', 0))}</strong></div>
  <div><span class="muted">Organizations</span><strong>{e(summary.get('ngos_supported', 0))}</strong></div>
</div>
<h2 style="margin-top:28px;font-size:16px">Impact by Cause</h2>
<table><thead><tr><th>Cause</th><th>Amount</th><th>Lives</th><th>Share</th></tr></thead>
<tbody>{cause_rows or '<tr><td colspan="4">No cause data</td></tr>'}</tbody></table>
<h2 style="margin-top:28px;font-size:16px">Highlights</h2>
<div class="kpi">{highlight_html}</div>
<h2 style="margin-top:28px;font-size:16px">Your Journey</h2>
<ul>{journey_html or '<li class="muted">No milestones yet.</li>'}</ul>
<p class="muted" style="margin-top:24px">Generated by Give Away. Lives impacted uses the platform rule of ₹{RUPEES_PER_LIFE} ≈ 1 life. This is an impact summary, not an 80G tax certificate.</p>
</div></body></html>"""
    filename = f"impact-report-{profile.get('donor_id', 'donor')}.html"
    return filename, "text/html; charset=utf-8", html
