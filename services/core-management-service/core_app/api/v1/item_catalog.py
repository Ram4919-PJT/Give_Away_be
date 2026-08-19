from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.schemas.item_donation import CatalogItemDetailOut, CatalogListResponse
from core_app.services import item_donation_service as service

router = APIRouter(prefix="/catalog", tags=["Item Catalog"])


@router.get("/items", response_model=CatalogListResponse)
async def list_available_items(
    category: str | None = Query(default=None),
    condition: str | None = Query(default=None),
    city: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    items, total = await service.list_available_catalog_items(
        db,
        category_slug=category,
        condition=condition,
        city=city,
        search=search,
        page=page,
        page_size=page_size,
    )
    return CatalogListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/items/{item_donation_id}", response_model=CatalogItemDetailOut)
async def get_catalog_item_detail(
    item_donation_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_catalog_item_detail(db, item_donation_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
