"""Authenticated donor pledges list, summary, impact, and download."""

from __future__ import annotations

from calendar import month_abbr
from datetime import date, datetime
from html import escape
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.pledges import DonorPledge
from core_app.models.profiles import DonorProfile, Program
from core_app.services.donor_dashboard_service import (
    CATEGORY_IMAGES,
    RUPEES_PER_LIFE,
    _normalize_category,
    _period_bounds,
)
from core_app.services.donor_donations_service import ORG_NAME, ORG_TAGLINE

ACTIVE = {"ACTIVE"}
COMPLETED = {"COMPLETED", "FULFILLED"}
CANCELLED = {"CANCELLED", "CANCELED"}


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _empty_summary() -> dict[str, Any]:
    return {
        "total_pledged": 0.0,
        "causes_count": 0,
        "active_count": 0,
        "active_remaining": 0.0,
        "completed_count": 0,
        "completed_fulfilled": 0.0,
        "upcoming_amount": 0.0,
        "upcoming_date": None,
        "upcoming_date_label": None,
    }


def _empty_impact() -> dict[str, Any]:
    return {
        "lives_impacted": 0,
        "children_educated": 0,
        "patients_supported": 0,
        "trees_planted": 0,
    }


async def _resolve_donor(db: AsyncSession, user_id: int) -> DonorProfile | None:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    return result.scalar_one_or_none()


def _end_date(start: date, months: int) -> date:
    # Approximate month add without extra deps
    y = start.year + (start.month - 1 + months) // 12
    m = (start.month - 1 + months) % 12 + 1
    d = min(start.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, d)


def _status_label(raw: str | None) -> str:
    s = (raw or "").upper()
    if s in COMPLETED:
        return "Completed"
    if s in CANCELLED:
        return "Cancelled"
    return "Active"


def _serialize_pledge(pledge: DonorPledge, program: Program | None) -> dict[str, Any]:
    monthly = _as_float(pledge.monthly_amount)
    duration = int(pledge.duration_months or 0)
    paid_count = int(pledge.payments_made or 0)
    total = round(monthly * duration, 2)
    paid = round(monthly * paid_count, 2)
    remaining = max(round(total - paid, 2), 0.0)
    cat = _normalize_category(program.category if program else None)
    start = pledge.start_date
    end = _end_date(start, duration) if start and duration else None
    status = _status_label(pledge.status)

    return {
        "id": f"pledge-{pledge.pledge_id}",
        "pledge_id": pledge.pledge_id,
        "title": program.program_name if program else "General Pledge",
        "ngo_name": pledge.organization_name or ORG_NAME,
        "category": cat,
        "monthly_amount": monthly,
        "monthly_label": f"₹{monthly:,.0f} / month" if monthly == int(monthly) else f"₹{monthly:,.2f} / month",
        "start_date": start.isoformat() if start else None,
        "start_label": start.strftime("%b %Y") if start else "—",
        "duration_months": duration,
        "duration_label": f"{duration} Months" if duration else "—",
        "date_range_label": (
            f"{start.strftime('%b %Y')} – {end.strftime('%b %Y')}" if start and end else "—"
        ),
        "total_pledged": total,
        "paid_so_far": paid,
        "remaining": remaining,
        "payments_made": paid_count,
        "payments_total": duration,
        "payments_label": f"{paid_count} / {duration} Payments" if duration else "—",
        "status": status,
        "raw_status": pledge.status,
        "payment_method": pledge.payment_method,
        "next_payment_date": pledge.next_payment_date.isoformat() if pledge.next_payment_date else None,
        "next_payment_label": (
            pledge.next_payment_date.strftime("%d %b %Y") if pledge.next_payment_date else None
        ),
        "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
    }


def _compute_impact(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive impact metrics from paid pledge amounts by category (documented rules)."""
    paid_by_cat: dict[str, float] = {}
    total_paid = 0.0
    for row in rows:
        if row["status"] == "Cancelled":
            continue
        paid = _as_float(row["paid_so_far"])
        total_paid += paid
        cat = row.get("category") or "Others"
        paid_by_cat[cat] = paid_by_cat.get(cat, 0.0) + paid

    lives = int(total_paid // RUPEES_PER_LIFE)
    children = int(paid_by_cat.get("Education", 0) // 1000)
    patients = int(
        (paid_by_cat.get("Healthcare", 0) + paid_by_cat.get("Medical", 0)) // 1500
    )
    trees = int(
        (
            paid_by_cat.get("Environment", 0)
            + paid_by_cat.get("Sanitation", 0)
            + paid_by_cat.get("Infrastructure", 0)
        )
        // 50
    )
    return {
        "lives_impacted": lives,
        "children_educated": children,
        "patients_supported": patients,
        "trees_planted": trees,
    }


def _in_period(start: date | None, period: str, now: datetime) -> bool:
    if not start:
        return True
    key = (period or "year").lower().replace("-", "_")
    if key in {"all", "all_time"}:
        return True
    cur_start, cur_end, _, _ = _period_bounds(period, now)
    dt = datetime.combine(start, datetime.min.time())
    return cur_start <= dt < cur_end


async def build_my_pledges(
    db: AsyncSession,
    *,
    user_id: int,
    period: str = "year",
    tab: str = "all",
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    profile = await _resolve_donor(db, user_id)
    if not profile:
        return {
            "has_profile": False,
            "empty": True,
            "period": period,
            "tab": tab,
            "category": category or "all",
            "page": page,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
            "categories": [],
            "summary": _empty_summary(),
            "impact": _empty_impact(),
            "upcoming_payments": [],
            "download_available": False,
            "items": [],
        }

    result = await db.execute(
        select(DonorPledge, Program)
        .join(Program, Program.program_id == DonorPledge.program_id, isouter=True)
        .where(DonorPledge.donor_id == profile.donor_id)
        .order_by(DonorPledge.start_date.desc(), DonorPledge.pledge_id.desc())
    )
    pairs = result.all()
    now = datetime.utcnow()
    all_rows = [_serialize_pledge(p, prog) for p, prog in pairs]

    # Summary over all pledges (lifetime), not just filtered tab
    causes = {r["category"] for r in all_rows if r.get("category")}
    active = [r for r in all_rows if r["status"] == "Active"]
    completed = [r for r in all_rows if r["status"] == "Completed"]
    upcoming_candidates = sorted(
        [r for r in active if r.get("next_payment_date")],
        key=lambda r: r["next_payment_date"],
    )
    next_up = upcoming_candidates[0] if upcoming_candidates else None

    summary = {
        "total_pledged": round(sum(r["total_pledged"] for r in all_rows if r["status"] != "Cancelled"), 2),
        "causes_count": len(causes),
        "active_count": len(active),
        "active_remaining": round(sum(r["remaining"] for r in active), 2),
        "completed_count": len(completed),
        "completed_fulfilled": round(sum(r["paid_so_far"] for r in completed), 2),
        "upcoming_amount": next_up["monthly_amount"] if next_up else 0.0,
        "upcoming_date": next_up["next_payment_date"] if next_up else None,
        "upcoming_date_label": next_up["next_payment_label"] if next_up else None,
    }

    impact = _compute_impact(all_rows)

    upcoming_payments = []
    for row in upcoming_candidates[:5]:
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
                "pledge_id": row["pledge_id"],
                "title": row["title"],
                "amount": row["monthly_amount"],
                "payment_method": row.get("payment_method") or "—",
                "type_label": "Monthly Pledge",
                "date": nd,
                "day_label": day_label,
                "month_label": mon_label,
            }
        )

    # Filter for table
    tab_key = (tab or "all").lower().replace("-", "_")
    rows = list(all_rows)
    if tab_key in {"active", "active_pledges"}:
        rows = [r for r in rows if r["status"] == "Active"]
    elif tab_key in {"completed", "completed_pledges"}:
        rows = [r for r in rows if r["status"] == "Completed"]
    elif tab_key in {"cancelled", "canceled", "cancelled_pledges"}:
        rows = [r for r in rows if r["status"] == "Cancelled"]

    rows = [r for r in rows if _in_period(
        date.fromisoformat(r["start_date"]) if r.get("start_date") else None,
        period,
        now,
    )]

    categories = sorted({r["category"] for r in all_rows if r.get("category")})
    cat_filter = (category or "").strip()
    if cat_filter and cat_filter.lower() not in {"all", "all causes", "all_causes"}:
        rows = [r for r in rows if (r.get("category") or "").lower() == cat_filter.lower()]

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
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "categories": categories,
        "summary": summary,
        "impact": impact,
        "upcoming_payments": upcoming_payments,
        "download_available": len(all_rows) > 0,
        "items": page_items,
        "profile": {
            "donor_id": profile.donor_id,
            "full_name": profile.full_name,
            "email": profile.email,
        },
        "benefits": [
            {
                "id": "tax",
                "title": "Tax Benefits",
                "description": "80G certified donations",
            },
            {
                "id": "updates",
                "title": "Priority Updates",
                "description": "Get regular impact updates",
            },
            {
                "id": "badge",
                "title": "Exclusive Badge",
                "description": "Earn badges for your pledges",
            },
        ],
    }


async def build_pledges_summary_download(
    db: AsyncSession,
    *,
    user_id: int,
) -> tuple[str, str, str]:
    payload = await build_my_pledges(
        db, user_id=user_id, period="all", tab="all", page=1, page_size=100
    )
    if not payload.get("has_profile"):
        raise LookupError("Donor profile not found")
    if not payload.get("items") and payload.get("empty"):
        raise LookupError("No pledges to download")

    profile = payload.get("profile") or {}
    summary = payload.get("summary") or {}
    donor = await _resolve_donor(db, user_id)
    if not donor:
        raise LookupError("Donor profile not found")
    result = await db.execute(
        select(DonorPledge, Program)
        .join(Program, Program.program_id == DonorPledge.program_id, isouter=True)
        .where(DonorPledge.donor_id == donor.donor_id)
        .order_by(DonorPledge.start_date.desc())
    )
    rows = [_serialize_pledge(p, prog) for p, prog in result.all()]
    if not rows:
        raise LookupError("No pledges to download")

    def e(v: Any) -> str:
        return escape(str(v if v is not None else "—"))

    body_rows = "".join(
        f"<tr><td>{e(r['title'])}</td><td>{e(r['ngo_name'])}</td>"
        f"<td>{e(r['monthly_label'])}</td><td>{e(r['duration_label'])}</td>"
        f"<td>₹{e(f'{r['total_pledged']:,.2f}')}</td><td>₹{e(f'{r['paid_so_far']:,.2f}')}</td>"
        f"<td>{e(r['status'])}</td></tr>"
        for r in rows
    )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Pledge Summary</title>
<style>
body{{font-family:Georgia,serif;color:#0B245B;background:#F4F7FC;margin:0}}
.sheet{{max-width:900px;margin:28px auto;background:#fff;border:1px solid #DCE8FA;border-radius:16px;padding:36px}}
h1{{margin:0;font-size:22px}} .muted{{color:#49638F;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin-top:20px;font-size:13px}}
th,td{{text-align:left;padding:10px 8px;border-bottom:1px solid #E8EEF8}}
th{{color:#49638F;font-size:11px;text-transform:uppercase}}
.kpi{{display:flex;gap:18px;flex-wrap:wrap;margin-top:18px}}
.kpi div{{background:#F7FAFF;border:1px solid #DCE8FA;border-radius:12px;padding:12px 14px;min-width:140px}}
.kpi strong{{display:block;font-size:18px;margin-top:4px}}
</style></head><body><div class="sheet">
<h1>{e(ORG_NAME)} — Pledge Summary</h1>
<p class="muted">{e(ORG_TAGLINE)} · Prepared for {e(profile.get('full_name'))}</p>
<div class="kpi">
  <div><span class="muted">Total Pledged</span><strong>₹{e(f"{summary.get('total_pledged',0):,.2f}")}</strong></div>
  <div><span class="muted">Active</span><strong>{e(summary.get('active_count',0))}</strong></div>
  <div><span class="muted">Completed</span><strong>{e(summary.get('completed_count',0))}</strong></div>
</div>
<table><thead><tr>
<th>Cause</th><th>Organization</th><th>Details</th><th>Duration</th><th>Total</th><th>Paid</th><th>Status</th>
</tr></thead><tbody>{body_rows}</tbody></table>
<p class="muted" style="margin-top:24px">Generated by Give Away. This is a pledge summary, not an 80G tax certificate.</p>
</div></body></html>"""
    filename = f"pledge-summary-{profile.get('donor_id', 'donor')}.html"
    return filename, "text/html; charset=utf-8", html
