from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, require_roles
from core_app.models.item_category import ItemCategory
from core_app.schemas.item_donation import ItemCategoryOut

router = APIRouter(prefix="/item-categories", tags=["Item Categories"])


@router.get("", response_model=list[ItemCategoryOut])
async def get_item_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ItemCategory)
        .where(ItemCategory.is_active.is_(True))
        .order_by(ItemCategory.sort_order, ItemCategory.name)
    )
    return list(result.scalars().all())
