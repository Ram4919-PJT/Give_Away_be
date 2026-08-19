"""Reverse/forward geocoding via OpenStreetMap Nominatim (no API key required)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from core_app.config import settings

_nominatim_lock = asyncio.Lock()
_last_request_at: float = 0.0


def _validate_coordinates(latitude: float, longitude: float) -> None:
    if not (-90 <= latitude <= 90):
        raise ValueError("Latitude must be between -90 and 90.")
    if not (-180 <= longitude <= 180):
        raise ValueError("Longitude must be between -180 and 180.")


def _parse_address_components(address: dict[str, Any]) -> dict[str, str | None]:
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("suburb")
        or address.get("county")
    )
    state = address.get("state")
    country = address.get("country")
    pincode = address.get("postcode")
    line1 = address.get("road") or address.get("neighbourhood") or address.get("suburb")
    return {
        "city": city,
        "state": state,
        "country": country,
        "pincode": pincode,
        "line1": line1,
    }


async def _throttled_get(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> httpx.Response:
    global _last_request_at
    async with _nominatim_lock:
        import time

        now = time.monotonic()
        wait = settings.NOMINATIM_MIN_INTERVAL_SEC - (now - _last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)
        response = await client.get(url, params=params)
        _last_request_at = time.monotonic()
        return response


async def reverse_geocode(latitude: float, longitude: float) -> dict[str, Any]:
    _validate_coordinates(latitude, longitude)
    url = f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}

    async with httpx.AsyncClient(timeout=settings.GEOCODING_TIMEOUT_SEC, headers=headers) as client:
        response = await _throttled_get(client, url, params)
        response.raise_for_status()
        data = response.json()

    address = data.get("address") or {}
    parts = _parse_address_components(address)
    display = data.get("display_name") or ", ".join(
        p for p in [parts.get("city"), parts.get("state"), parts.get("country")] if p
    )
    return {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "city": parts.get("city"),
        "state": parts.get("state"),
        "country": parts.get("country"),
        "pincode": parts.get("pincode"),
        "line1": parts.get("line1"),
        "formatted_address": display,
    }


async def forward_geocode_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if len(q) < 2:
        return []

    url = f"{settings.NOMINATIM_BASE_URL.rstrip('/')}/search"
    params = {
        "q": q,
        "format": "json",
        "addressdetails": 1,
        "limit": min(max(limit, 1), 10),
        "countrycodes": settings.NOMINATIM_COUNTRY_CODES or None,
    }
    params = {k: v for k, v in params.items() if v is not None}
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}

    async with httpx.AsyncClient(timeout=settings.GEOCODING_TIMEOUT_SEC, headers=headers) as client:
        response = await _throttled_get(client, url, params)
        response.raise_for_status()
        rows = response.json()

    results: list[dict[str, Any]] = []
    for row in rows:
        try:
            lat = float(row["lat"])
            lng = float(row["lon"])
            _validate_coordinates(lat, lng)
        except (KeyError, TypeError, ValueError):
            continue
        address = row.get("address") or {}
        parts = _parse_address_components(address)
        results.append(
            {
                "latitude": lat,
                "longitude": lng,
                "city": parts.get("city"),
                "state": parts.get("state"),
                "country": parts.get("country"),
                "pincode": parts.get("pincode"),
                "formatted_address": row.get("display_name"),
            }
        )
    return results
