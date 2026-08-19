"""Resolve user contact details from IAM."""

from __future__ import annotations

import logging

import httpx

from comm_app.config import settings

logger = logging.getLogger(__name__)


async def resolve_user_contact(user_id: int) -> dict | None:
    if not user_id:
        return None
    url = f"{settings.GATEWAY_INTERNAL_URL.rstrip('/')}/api/v1/users/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
            data = response.json()
            email = data.get("email")
            if not email or str(email).endswith("@deleted.local"):
                return None
            return {
                "user_id": user_id,
                "email": str(email),
                "name": data.get("full_name") or data.get("name") or "there",
            }
    except Exception as exc:
        logger.warning("Failed to resolve IAM user %s: %s", user_id, exc)
        return None
