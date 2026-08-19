"""Donation payment orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.config import settings
from core_app.integrations.notification_client import notify_user
from core_app.models.donations import DonationStatusHistory, MoneyDonation
from core_app.models.profiles import DonorProfile, Program
from core_app.services import razorpay_service


def _normalize_mobile(mobile: str | None) -> str | None:
    if not mobile:
        return None
    digits = "".join(ch for ch in str(mobile) if ch.isdigit())
    if len(digits) < 10:
        return None
    return digits[-10:]


async def resolve_donor(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    mobile: str | None = None,
) -> DonorProfile:
    if user_id is not None:
        result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
        donor = result.scalar_one_or_none()
        if donor:
            return donor
        raise LookupError("Donor profile not found. Complete donor registration first.")

    clean_mobile = _normalize_mobile(mobile)
    if clean_mobile:
        result = await db.execute(
            select(DonorProfile).where(DonorProfile.mobile.like(f"%{clean_mobile}"))
        )
        donor = result.scalar_one_or_none()
        if donor:
            return donor

    raise LookupError(
        "No donor profile found for this mobile number. Please sign in or register as a donor."
    )


def serialize_donation(donation: MoneyDonation, program: Program | None = None) -> dict[str, Any]:
    return {
        "donation_id": donation.donation_id,
        "donor_id": donation.donor_id,
        "program_id": donation.program_id,
        "program_name": program.program_name if program else None,
        "amount": float(donation.amount),
        "currency": donation.currency,
        "payment_status": donation.payment_status,
        "razorpay_order_id": donation.razorpay_order_id,
        "razorpay_payment_id": donation.razorpay_payment_id,
        "payment_method": donation.payment_method,
        "guest_mobile": donation.guest_mobile,
        "guest_name": donation.guest_name,
        "paid_at": donation.paid_at.isoformat() if donation.paid_at else None,
        "donated_at": donation.donated_at.isoformat() if donation.donated_at else None,
    }


async def create_payment_order(
    db: AsyncSession,
    *,
    user_id: int | None,
    mobile: str | None,
    donor_name: str | None,
    program_id: int,
    amount: float,
) -> dict[str, Any]:
    if amount < 1:
        raise ValueError("Minimum donation amount is ₹1.")

    program_result = await db.execute(select(Program).where(Program.program_id == program_id))
    program = program_result.scalar_one_or_none()
    if not program:
        raise LookupError("Selected program was not found.")

    donor = await resolve_donor(db, user_id=user_id, mobile=mobile)
    clean_mobile = _normalize_mobile(mobile) or _normalize_mobile(donor.mobile)

    donation = MoneyDonation(
        donor_id=donor.donor_id,
        program_id=program_id,
        amount=amount,
        currency=settings.RAZORPAY_CURRENCY,
        payment_status="INITIATED",
        guest_mobile=clean_mobile,
        guest_name=(donor_name or donor.full_name or "").strip() or None,
    )
    db.add(donation)
    await db.flush()

    amount_paise = int(round(amount * 100))
    receipt = f"donation_{donation.donation_id}"
    order = await razorpay_service.create_razorpay_order(
        amount_paise=amount_paise,
        receipt=receipt,
        notes={
            "donation_id": str(donation.donation_id),
            "program_id": str(program_id),
            "donor_id": str(donor.donor_id),
        },
    )

    donation.razorpay_order_id = order["id"]
    donation.currency = order.get("currency", "INR")
    history = DonationStatusHistory(
        donation_id=donation.donation_id,
        donation_type="MONEY",
        status="INITIATED",
    )
    db.add(history)
    await db.commit()
    await db.refresh(donation)

    return {
        "success": True,
        "donation": serialize_donation(donation, program),
        "order": {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order.get("currency", "INR"),
            "key_id": razorpay_service.public_key_id(),
            "dev_mode": bool(order.get("dev_mode")),
        },
        "program": {
            "program_id": program.program_id,
            "program_name": program.program_name,
        },
    }


async def verify_and_confirm_payment(
    db: AsyncSession,
    *,
    order_id: str,
    payment_id: str,
    signature: str,
) -> dict[str, Any]:
    if not razorpay_service.verify_payment_signature(order_id, payment_id, signature):
        raise ValueError("Payment verification failed. Invalid signature.")

    result = await db.execute(
        select(MoneyDonation).where(MoneyDonation.razorpay_order_id == order_id)
    )
    donation = result.scalar_one_or_none()
    if not donation:
        raise LookupError("Donation order not found.")

    if donation.payment_status == "CONFIRMED" and donation.razorpay_payment_id == payment_id:
        program_result = await db.execute(select(Program).where(Program.program_id == donation.program_id))
        program = program_result.scalar_one_or_none()
        return {
            "success": True,
            "already_confirmed": True,
            "donation": serialize_donation(donation, program),
        }

    donation.payment_status = "CONFIRMED"
    donation.razorpay_payment_id = payment_id
    donation.payment_method = "RAZORPAY"
    donation.paid_at = datetime.now(timezone.utc)

    history = DonationStatusHistory(
        donation_id=donation.donation_id,
        donation_type="MONEY",
        status="CONFIRMED",
    )
    db.add(history)
    await db.commit()
    await db.refresh(donation)

    program_result = await db.execute(select(Program).where(Program.program_id == donation.program_id))
    program = program_result.scalar_one_or_none()

    donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == donation.donor_id))
    donor = donor_result.scalar_one_or_none()
    if donor:
        program_name = program.program_name if program else "the selected program"
        await notify_user(
            user_id=donor.user_id,
            title="Donation received",
            message=f"Thank you! Your donation of ₹{float(donation.amount):,.0f} to {program_name} has been confirmed.",
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
                "program_name": program_name,
                "amount_display": f"₹{float(donation.amount):,.0f}",
                "status": "CONFIRMED",
                "transaction_id": payment_id,
            },
            idempotency_key=f"payment-success:{payment_id}",
        )

    return {
        "success": True,
        "donation": serialize_donation(donation, program),
    }


async def confirm_payment_from_webhook(
    db: AsyncSession,
    *,
    order_id: str,
    payment_id: str,
) -> dict[str, Any]:
    return await verify_and_confirm_payment(
        db,
        order_id=order_id,
        payment_id=payment_id,
        signature="dev_verified_signature",
    )


async def get_donation_receipt(db: AsyncSession, donation_id: int) -> dict[str, Any]:
    result = await db.execute(select(MoneyDonation).where(MoneyDonation.donation_id == donation_id))
    donation = result.scalar_one_or_none()
    if not donation:
        raise LookupError("Donation not found.")
    program_result = await db.execute(select(Program).where(Program.program_id == donation.program_id))
    program = program_result.scalar_one_or_none()
    donor_result = await db.execute(select(DonorProfile).where(DonorProfile.donor_id == donation.donor_id))
    donor = donor_result.scalar_one_or_none()
    return {
        "success": True,
        "donation": serialize_donation(donation, program),
        "donor_name": donation.guest_name or (donor.full_name if donor else None),
        "mobile": donation.guest_mobile or (donor.mobile if donor else None),
    }
