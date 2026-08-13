"""Authenticated donor donation list + acknowledgment receipts."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.donations import ItemDonation, MoneyDonation
from core_app.models.profiles import DonorProfile, Program
from core_app.services.donor_recurring_gifts_service import (
    count_active_recurring_gifts,
    list_recurring_gifts_for_donations,
)
from core_app.services.donor_dashboard_service import (
    CATEGORY_IMAGES,
    CONFIRMED_MONEY,
    RUPEES_PER_LIFE,
    _as_dt,
    _as_float,
    _growth_pct,
    _money_status_label,
    _item_status_label,
    _normalize_category,
    _period_bounds,
)

ORG_NAME = "Aja Abayahastham"
ORG_TAGLINE = "Serve · Support · Uplift"


def _empty_summary() -> dict[str, Any]:
    return {
        "total_donated": 0.0,
        "lives_impacted": 0,
        "donations_count": 0,
        "donation_growth_pct": 0.0,
        "impact_growth_pct": 0.0,
        "top_cause": None,
    }


async def _resolve_donor(db: AsyncSession, user_id: int) -> DonorProfile | None:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    return result.scalar_one_or_none()


def _serialize_money(
    donation: MoneyDonation,
    program: Program | None,
    dt: datetime,
) -> dict[str, Any]:
    cat = _normalize_category(program.category if program else None)
    return {
        "id": f"money-{donation.donation_id}",
        "donation_id": donation.donation_id,
        "type": "MONEY",
        "donation_kind": "one_time",
        "title": program.program_name if program else "General Support",
        "ngo_name": ORG_NAME,
        "category": cat,
        "date": dt.date().isoformat(),
        "date_label": dt.strftime("%b %d, %Y"),
        "time_label": dt.strftime("%I:%M %p").lstrip("0"),
        "amount": round(_as_float(donation.amount), 2),
        "quantity": None,
        "status": _money_status_label(donation.payment_status),
        "raw_status": donation.payment_status,
        "payment_method": None,
        "receipt_available": (donation.payment_status or "").upper() in CONFIRMED_MONEY,
        "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
        "sort_at": dt.isoformat(),
    }


def _serialize_item(item: ItemDonation) -> dict[str, Any]:
    cat = _normalize_category(item.category)
    return {
        "id": f"item-{item.item_donation_id}",
        "donation_id": item.item_donation_id,
        "type": "ITEM",
        "donation_kind": "one_time",
        "title": item.description[:80] if item.description else (item.category or "Item Donation"),
        "ngo_name": ORG_NAME,
        "category": cat,
        "date": None,
        "date_label": "Recently",
        "time_label": None,
        "amount": None,
        "quantity": item.quantity,
        "status": _item_status_label(item.status),
        "raw_status": item.status,
        "payment_method": None,
        "receipt_available": (item.status or "").upper()
        in {"RECEIVED", "DELIVERED", "COMPLETED", "DISTRIBUTED", "LISTED", "PICKUP_SCHEDULED"},
        "image_url": CATEGORY_IMAGES.get(cat, CATEGORY_IMAGES["Education"]),
        "sort_at": f"0000-{item.item_donation_id:08d}",
    }


async def build_my_donations(
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
            "footer": {"last_donation": None, "recurring_count": 0, "pledged_total": None},
            "items": [],
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
    period_key = (period or "year").lower().replace("-", "_")
    use_all_time = period_key in {"all", "all_time"}

    if use_all_time:
        cur_start = datetime(1970, 1, 1)
        cur_end = now
        prev_start = datetime(1970, 1, 1)
        prev_end = datetime(1970, 1, 1)
    else:
        cur_start, cur_end, prev_start, prev_end = _period_bounds(period, now)

    money_items: list[dict[str, Any]] = []
    confirmed_in_period: list[tuple[float, datetime, str]] = []
    confirmed_prev: list[float] = []
    all_confirmed_amounts: list[tuple[float, str]] = []

    for donation, program in money_rows:
        dt = _as_dt(donation.donated_at) or now
        row = _serialize_money(donation, program, dt)
        money_items.append(row)
        if (donation.payment_status or "").upper() in CONFIRMED_MONEY:
            amt = _as_float(donation.amount)
            cat = row["category"]
            all_confirmed_amounts.append((amt, cat))
            if cur_start <= dt < cur_end:
                confirmed_in_period.append((amt, dt, cat))
            if prev_start <= dt < prev_end:
                confirmed_prev.append(amt)

    item_items = [_serialize_item(item) for item in item_rows]

    # Summary (period-aware for money; items always counted when present)
    period_total = sum(a for a, _, _ in confirmed_in_period)
    prev_total = sum(confirmed_prev)
    lifetime_total = sum(a for a, _ in all_confirmed_amounts)

    lives = int(lifetime_total // RUPEES_PER_LIFE)
    lives += sum(
        int(item.quantity or 0)
        for item in item_rows
        if (item.status or "").upper() in {"RECEIVED", "DELIVERED", "COMPLETED", "DISTRIBUTED"}
    )

    cause_amounts: dict[str, float] = {}
    for amt, _, cat in confirmed_in_period:
        cause_amounts[cat] = cause_amounts.get(cat, 0.0) + amt
    if not cause_amounts:
        for amt, cat in all_confirmed_amounts:
            cause_amounts[cat] = cause_amounts.get(cat, 0.0) + amt

    breakdown_total = sum(cause_amounts.values()) or 1.0
    top_cause = None
    if cause_amounts:
        name, amount = max(cause_amounts.items(), key=lambda x: x[1])
        top_cause = {
            "name": name,
            "amount": round(amount, 2),
            "percent": round((amount / breakdown_total) * 100, 1),
        }

    donations_count = len(
        [
            r
            for r in money_items
            if (r.get("raw_status") or "").upper() in CONFIRMED_MONEY
            and r.get("date")
            and (
                use_all_time
                or (
                    cur_start
                    <= (_as_dt(r["sort_at"]) or now)
                    < cur_end
                )
            )
        ]
    ) + len(
        [
            i
            for i in item_rows
            if (i.status or "").upper() in {"RECEIVED", "DELIVERED", "COMPLETED", "DISTRIBUTED"}
        ]
    )

    summary = {
        "total_donated": round(period_total if not use_all_time else lifetime_total, 2),
        "lives_impacted": lives,
        "donations_count": donations_count if donations_count else len(money_items) + len(item_items),
        "donation_growth_pct": _growth_pct(period_total, prev_total),
        "impact_growth_pct": _growth_pct(
            float(int(period_total // RUPEES_PER_LIFE)),
            float(int(prev_total // RUPEES_PER_LIFE)),
        ),
        "top_cause": top_cause,
    }

    # Build filterable list
    tab_key = (tab or "all").lower().replace("-", "_")
    rows: list[dict[str, Any]] = []

    if tab_key in {"all", "one_time", "one_time_donations"}:
        for row in money_items:
            dt = _as_dt(row["sort_at"]) or now
            if not use_all_time and not (cur_start <= dt < cur_end):
                continue
            rows.append(row)
        if tab_key == "all":
            # Items have no reliable date — include for all-time / year views
            if use_all_time or period_key in {"year", "this_year"}:
                rows.extend(item_items)
    elif tab_key in {"recurring", "recurring_donations"}:
        rows = await list_recurring_gifts_for_donations(db, donor_id=donor_id)
    elif tab_key in {"pledges", "pledge"}:
        rows = []  # not supported yet
    else:
        for row in money_items:
            dt = _as_dt(row["sort_at"]) or now
            if not use_all_time and not (cur_start <= dt < cur_end):
                continue
            rows.append(row)
        rows.extend(item_items)

    categories = sorted(
        {
            r["category"]
            for r in money_items + item_items
            if r.get("category")
        }
    )

    cat_filter = (category or "").strip()
    if cat_filter and cat_filter.lower() not in {"all", "all causes", "all_causes"}:
        rows = [r for r in rows if (r.get("category") or "").lower() == cat_filter.lower()]

    # Sort: money by date desc, then items
    money_sorted = [r for r in rows if r.get("type") == "MONEY"]
    item_sorted = [r for r in rows if r.get("type") != "MONEY"]
    money_sorted.sort(key=lambda r: r.get("date") or "", reverse=True)
    ordered = money_sorted + item_sorted

    total = len(ordered)
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    total_pages = (total + page_size - 1) // page_size if total else 0
    start = (page - 1) * page_size
    page_items = ordered[start : start + page_size]

    # Strip internal sort key
    for item in page_items:
        item.pop("sort_at", None)

    last_donation = None
    if money_sorted:
        last = money_sorted[0]
        last_donation = {
            "date_label": last.get("date_label"),
            "amount": last.get("amount"),
            "title": last.get("title"),
        }

    return {
        "has_profile": True,
        "empty": total == 0 and not money_items and not item_items,
        "period": period,
        "tab": tab,
        "category": cat_filter or "all",
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "categories": categories,
        "summary": summary,
        "footer": {
            "last_donation": last_donation,
            "recurring_count": await count_active_recurring_gifts(db, donor_id=donor_id),
            "pledged_total": None,
        },
        "items": page_items,
        "profile": {
            "donor_id": profile.donor_id,
            "full_name": profile.full_name,
            "email": profile.email,
            "mobile": profile.mobile,
        },
    }


async def build_donation_receipt(
    db: AsyncSession,
    *,
    user_id: int,
    donation_key: str,
) -> tuple[str, str, str]:
    """
    Returns (filename, content_type, html_body) for an acknowledgment receipt.
    donation_key: "money-123" | "item-45" | bare numeric id (money).
    """
    profile = await _resolve_donor(db, user_id)
    if not profile:
        raise LookupError("Donor profile not found")

    key = (donation_key or "").strip().lower()
    donation_type = "MONEY"
    donation_id: int | None = None

    if key.startswith("money-"):
        donation_type = "MONEY"
        donation_id = int(key.split("-", 1)[1])
    elif key.startswith("item-"):
        donation_type = "ITEM"
        donation_id = int(key.split("-", 1)[1])
    elif key.isdigit():
        donation_type = "MONEY"
        donation_id = int(key)
    else:
        raise LookupError("Invalid donation id")

    if donation_type == "MONEY":
        result = await db.execute(
            select(MoneyDonation, Program)
            .join(Program, Program.program_id == MoneyDonation.program_id, isouter=True)
            .where(
                MoneyDonation.donation_id == donation_id,
                MoneyDonation.donor_id == profile.donor_id,
            )
        )
        row = result.first()
        if not row:
            raise LookupError("Donation not found")
        donation, program = row
        if (donation.payment_status or "").upper() not in CONFIRMED_MONEY:
            raise PermissionError("Receipt available only for confirmed donations")
        dt = _as_dt(donation.donated_at) or datetime.utcnow()
        payload = {
            "receipt_no": f"GA-M-{donation.donation_id:06d}",
            "donation_id": donation.donation_id,
            "type_label": "Money Donation",
            "donor_name": profile.full_name,
            "donor_email": profile.email,
            "donor_mobile": profile.mobile,
            "amount_label": f"₹{_as_float(donation.amount):,.2f}",
            "cause": program.program_name if program else "General Support",
            "category": _normalize_category(program.category if program else None),
            "date_label": dt.strftime("%d %b %Y, %I:%M %p").lstrip("0"),
            "status": _money_status_label(donation.payment_status),
            "org": ORG_NAME,
            "tagline": ORG_TAGLINE,
            "note": (
                "This is a donation acknowledgment receipt generated by Give Away. "
                "It is not an 80G tax certificate."
            ),
        }
        filename = f"receipt-{payload['receipt_no']}.html"
    else:
        result = await db.execute(
            select(ItemDonation).where(
                ItemDonation.item_donation_id == donation_id,
                ItemDonation.donor_id == profile.donor_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise LookupError("Donation not found")
        payload = {
            "receipt_no": f"GA-I-{item.item_donation_id:06d}",
            "donation_id": item.item_donation_id,
            "type_label": "Item Donation",
            "donor_name": profile.full_name,
            "donor_email": profile.email,
            "donor_mobile": profile.mobile,
            "amount_label": f"{item.quantity} item(s)",
            "cause": item.description[:120] if item.description else (item.category or "Item Donation"),
            "category": _normalize_category(item.category),
            "date_label": "Date on record with pickup scheduling",
            "status": _item_status_label(item.status),
            "org": ORG_NAME,
            "tagline": ORG_TAGLINE,
            "note": (
                "This is an item donation acknowledgment. "
                "It is not an 80G tax certificate."
            ),
        }
        filename = f"receipt-{payload['receipt_no']}.html"

    html = _render_receipt_html(payload)
    return filename, "text/html; charset=utf-8", html


def _render_receipt_html(p: dict[str, Any]) -> str:
    def e(v: Any) -> str:
        return escape(str(v if v is not None else "—"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Receipt {e(p['receipt_no'])}</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; color: #0B245B; margin: 0; background: #F4F7FC; }}
    .sheet {{ max-width: 720px; margin: 32px auto; background: #fff; border: 1px solid #DCE8FA; border-radius: 16px; padding: 40px 44px; }}
    .brand {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1268E8; padding-bottom: 16px; }}
    .brand h1 {{ margin: 0; font-size: 22px; }}
    .brand p {{ margin: 4px 0 0; color: #49638F; font-size: 12px; }}
    .badge {{ background: #EEF5FF; color: #1268E8; font-weight: 700; font-size: 12px; padding: 6px 10px; border-radius: 999px; }}
    h2 {{ margin: 28px 0 8px; font-size: 20px; }}
    .meta {{ color: #49638F; font-size: 13px; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px 0; border-bottom: 1px solid #E8EEF8; font-size: 14px; }}
    th {{ color: #49638F; font-weight: 600; width: 40%; }}
    .amount {{ font-size: 28px; font-weight: 800; color: #1268E8; margin: 8px 0 20px; }}
    .note {{ margin-top: 28px; font-size: 12px; color: #49638F; line-height: 1.5; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #8AA0C2; text-align: center; }}
    @media print {{ body {{ background: #fff; }} .sheet {{ border: none; margin: 0; }} }}
  </style>
</head>
<body>
  <div class="sheet">
    <div class="brand">
      <div>
        <h1>{e(p['org'])}</h1>
        <p>{e(p['tagline'])}</p>
      </div>
      <span class="badge">Donation Receipt</span>
    </div>
    <h2>Thank you for your contribution</h2>
    <p class="meta">Receipt No. <strong>{e(p['receipt_no'])}</strong></p>
    <div class="amount">{e(p['amount_label'])}</div>
    <table>
      <tr><th>Donor Name</th><td>{e(p['donor_name'])}</td></tr>
      <tr><th>Email</th><td>{e(p['donor_email'])}</td></tr>
      <tr><th>Mobile</th><td>{e(p['donor_mobile'])}</td></tr>
      <tr><th>Donation Type</th><td>{e(p['type_label'])}</td></tr>
      <tr><th>Cause / Description</th><td>{e(p['cause'])}</td></tr>
      <tr><th>Category</th><td>{e(p['category'])}</td></tr>
      <tr><th>Date</th><td>{e(p['date_label'])}</td></tr>
      <tr><th>Status</th><td>{e(p['status'])}</td></tr>
      <tr><th>Organization</th><td>{e(p['org'])}</td></tr>
    </table>
    <p class="note">{e(p['note'])}</p>
    <p class="footer">Generated by Give Away · {e(p['org'])}</p>
  </div>
</body>
</html>
"""
