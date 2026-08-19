from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user, require_roles
from core_app.services import geocoding_service, location_service

router = APIRouter(tags=["Location"])


class LocationCoordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class SaveLocationRequest(LocationCoordinates):
    city: str | None = None
    state: str | None = None
    country: str | None = None


class NgoLocationRequest(SaveLocationRequest):
    line1: str | None = None
    pincode: str | None = None


@router.get("/location/search")
async def search_locations(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(8, ge=1, le=10),
    _user: TokenUser = Depends(get_current_user),
):
    """Forward geocode a place name (authenticated to reduce abuse)."""
    try:
        results = await geocoding_service.forward_geocode_search(q, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Location search is temporarily unavailable.",
        ) from exc
    return {"success": True, "query": q.strip(), "results": results}


@router.get("/location/me")
async def get_my_location(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await location_service.get_donor_location(db, user.user_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/location/me")
async def save_my_location(
    body: SaveLocationRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("DONOR")),
):
    try:
        return await location_service.save_donor_location(
            db,
            user_id=user.user_id,
            latitude=body.latitude,
            longitude=body.longitude,
            city=body.city,
            state=body.state,
            country=body.country,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/location/ngo/me")
async def save_ngo_location(
    body: NgoLocationRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(require_roles("NGO")),
):
    try:
        return await location_service.save_ngo_address_location(
            db,
            user_id=user.user_id,
            latitude=body.latitude,
            longitude=body.longitude,
            line1=body.line1,
            city=body.city,
            state=body.state,
            pincode=body.pincode,
            country=body.country,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/ngos/nearby")
async def get_nearby_ngos(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(10, ge=1, le=100, description="Search radius in km"),
    db: AsyncSession = Depends(get_db),
):
    """Public nearby NGO discovery — returns city-level info only, not exact donor coords."""
    try:
        return await location_service.find_nearby_ngos(
            db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius,
            verified_only=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
