"""Donor location persistence and nearby NGO queries."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.profiles import Address, DonorProfile, NgoProfile
from core_app.services import geocoding_service


def validate_coordinates(latitude: float, longitude: float) -> None:
    geocoding_service._validate_coordinates(latitude, longitude)


def validate_radius_km(radius: float) -> float:
    r = float(radius)
    if r <= 0 or r > 100:
        raise ValueError("Radius must be between 0 and 100 km.")
    return r


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


async def get_donor_by_user_id(db: AsyncSession, user_id: int) -> DonorProfile | None:
    result = await db.execute(select(DonorProfile).where(DonorProfile.user_id == user_id))
    return result.scalar_one_or_none()


def serialize_donor_location(donor: DonorProfile) -> dict[str, Any] | None:
    if donor.location_latitude is None or donor.location_longitude is None:
        return None
    return {
        "latitude": float(donor.location_latitude),
        "longitude": float(donor.location_longitude),
        "city": donor.location_city,
        "state": donor.location_state,
        "country": donor.location_country,
        "updated_at": donor.location_updated_at.isoformat() if donor.location_updated_at else None,
        "label": ", ".join(
            p for p in [donor.location_city, donor.location_state] if p
        ) or None,
    }


async def save_donor_location(
    db: AsyncSession,
    *,
    user_id: int,
    latitude: float,
    longitude: float,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
) -> dict[str, Any]:
    validate_coordinates(latitude, longitude)
    donor = await get_donor_by_user_id(db, user_id)
    if not donor:
        raise LookupError("Donor profile not found.")

    if not city and not state:
        geo = await geocoding_service.reverse_geocode(latitude, longitude)
        city = geo.get("city") or city
        state = geo.get("state") or state
        country = geo.get("country") or country

    donor.location_latitude = latitude
    donor.location_longitude = longitude
    donor.location_city = city
    donor.location_state = state
    donor.location_country = country
    donor.location_updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(donor)
    loc = serialize_donor_location(donor)
    return {"success": True, "location": loc}


async def get_donor_location(db: AsyncSession, user_id: int) -> dict[str, Any]:
    donor = await get_donor_by_user_id(db, user_id)
    if not donor:
        raise LookupError("Donor profile not found.")
    loc = serialize_donor_location(donor)
    return {"success": True, "location": loc}


async def find_nearby_ngos(
    db: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
    verified_only: bool = True,
) -> dict[str, Any]:
    validate_coordinates(latitude, longitude)
    radius_km = validate_radius_km(radius_km)

    stmt = (
        select(NgoProfile, Address)
        .join(Address, NgoProfile.address_id == Address.address_id)
        .where(Address.latitude.isnot(None), Address.longitude.isnot(None))
    )
    if verified_only:
        stmt = stmt.where(NgoProfile.verification_status == "VERIFIED")

    result = await db.execute(stmt)
    rows = result.all()

    ngos: list[dict[str, Any]] = []
    for ngo, address in rows:
        lat = float(address.latitude)
        lng = float(address.longitude)
        dist = haversine_km(latitude, longitude, lat, lng)
        if dist > radius_km:
            continue
        ngos.append(
            {
                "ngo_id": ngo.ngo_id,
                "name": ngo.ngo_name,
                "city": address.city,
                "state": address.state,
                "country": address.country,
                "latitude": lat,
                "longitude": lng,
                "verification_status": ngo.verification_status,
                "distance_km": round(dist, 2),
            }
        )

    ngos.sort(key=lambda n: n["distance_km"])
    return {
        "success": True,
        "location": {"latitude": latitude, "longitude": longitude},
        "radius_km": radius_km,
        "ngos": ngos,
        "count": len(ngos),
    }


async def save_ngo_address_location(
    db: AsyncSession,
    *,
    user_id: int,
    latitude: float,
    longitude: float,
    line1: str | None = None,
    city: str | None = None,
    state: str | None = None,
    pincode: str | None = None,
    country: str | None = None,
) -> dict[str, Any]:
    validate_coordinates(latitude, longitude)
    result = await db.execute(select(NgoProfile).where(NgoProfile.user_id == user_id))
    ngo = result.scalar_one_or_none()
    if not ngo:
        raise LookupError("NGO profile not found.")

    if not city or not state:
        geo = await geocoding_service.reverse_geocode(latitude, longitude)
        city = city or geo.get("city") or "Unknown"
        state = state or geo.get("state") or "Unknown"
        country = country or geo.get("country")
        pincode = pincode or geo.get("pincode") or "000000"
        line1 = line1 or geo.get("line1") or geo.get("formatted_address") or line1 or city

    if ngo.address_id:
        addr_result = await db.execute(select(Address).where(Address.address_id == ngo.address_id))
        address = addr_result.scalar_one_or_none()
    else:
        address = None

    if not address:
        address = Address(
            line1=line1 or city,
            city=city,
            state=state,
            pincode=pincode or "000000",
        )
        db.add(address)
        await db.flush()
        ngo.address_id = address.address_id
    else:
        if line1:
            address.line1 = line1
        address.city = city
        address.state = state
        if pincode:
            address.pincode = pincode

    address.latitude = latitude
    address.longitude = longitude
    address.country = country
    await db.commit()
    await db.refresh(address)

    return {
        "success": True,
        "location": {
            "latitude": float(address.latitude),
            "longitude": float(address.longitude),
            "city": address.city,
            "state": address.state,
            "country": address.country,
            "line1": address.line1,
            "pincode": address.pincode,
        },
    }
