"""Razorpay order creation and signature verification."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

import httpx

from core_app.config import settings

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def is_razorpay_configured() -> bool:
    return bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)


def is_dev_payment_mode() -> bool:
    return settings.PAYMENT_DEV_MODE or not is_razorpay_configured()


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    if not signature:
        return False
    if is_dev_payment_mode() and signature == "dev_verified_signature":
        return True
    if not settings.RAZORPAY_KEY_SECRET:
        return False
    payload = f"{order_id}|{payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    if not signature or not settings.RAZORPAY_WEBHOOK_SECRET:
        return False
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def create_razorpay_order(
    *,
    amount_paise: int,
    receipt: str,
    notes: dict[str, str] | None = None,
) -> dict[str, Any]:
    if amount_paise < 100:
        raise ValueError("Minimum donation amount is ₹1.")

    if is_dev_payment_mode():
        order_id = f"order_dev_{receipt}_{secrets.token_hex(4)}"
        return {
            "id": order_id,
            "amount": amount_paise,
            "currency": settings.RAZORPAY_CURRENCY,
            "receipt": receipt,
            "status": "created",
            "dev_mode": True,
        }

    payload = {
        "amount": amount_paise,
        "currency": settings.RAZORPAY_CURRENCY,
        "receipt": receipt,
        "notes": notes or {},
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{RAZORPAY_API_BASE}/orders",
            json=payload,
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        )
        response.raise_for_status()
        data = response.json()
    data["dev_mode"] = False
    return data


def public_key_id() -> str:
    if settings.RAZORPAY_KEY_ID:
        return settings.RAZORPAY_KEY_ID
    return "rzp_test_not_configured"
