from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user
from core_app.dependencies.ngo_auth import SUSPENDED_DETAIL, VERIFIED_ONLY_DETAIL
from core_app.models.funds import Allocation
from core_app.models.inventory import InventoryItem, InventoryTransaction
from core_app.services.ngo_service import is_ngo_suspended, is_ngo_verified, require_ngo_profile

router = APIRouter(prefix="/inventory", tags=["Inventory"])


class ItemStockCreate(BaseModel):
    category: str
    description: str
    quantity: int


class StockAllocateRequest(BaseModel):
    ngo_request_id: int
    item_id: int
    quantity_allocated: int


@router.get("")
async def list_inventory(
    db: AsyncSession = Depends(get_db),
    user: TokenUser = Depends(get_current_user),
):
    if user.role == "NGO":
        try:
            profile = await require_ngo_profile(db, user.user_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        if is_ngo_suspended(profile):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SUSPENDED_DETAIL)
        if not is_ngo_verified(profile):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=VERIFIED_ONLY_DETAIL)

    result = await db.execute(select(InventoryItem))
    return result.scalars().all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_inventory_item(data: ItemStockCreate, db: AsyncSession = Depends(get_db)):
    item = InventoryItem(
        category=data.category,
        description=data.description,
        quantity=data.quantity,
        status="IN_STOCK" if data.quantity > 0 else "OUT_OF_STOCK",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    tx = InventoryTransaction(item_id=item.item_id, transaction_type="IN", quantity=data.quantity)
    db.add(tx)
    await db.commit()
    return item


@router.get("/transactions")
async def list_transactions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InventoryTransaction))
    return result.scalars().all()


@router.get("/allocations")
async def list_allocations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Allocation))
    return result.scalars().all()


@router.post("/allocate", status_code=status.HTTP_201_CREATED)
async def allocate_item(data: StockAllocateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InventoryItem).where(InventoryItem.item_id == data.item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"Inventory item #{data.item_id} not found")

    if item.quantity < data.quantity_allocated:
        raise HTTPException(status_code=400, detail=f"Insufficient stock (Available: {item.quantity})")

    item.quantity -= data.quantity_allocated
    if item.quantity == 0:
        item.status = "OUT_OF_STOCK"

    alloc = Allocation(
        ngo_request_id=data.ngo_request_id,
        item_id=data.item_id,
        quantity_allocated=data.quantity_allocated,
    )
    db.add(alloc)

    tx = InventoryTransaction(item_id=data.item_id, transaction_type="OUT", quantity=data.quantity_allocated)
    db.add(tx)

    await db.commit()
    await db.refresh(alloc)
    return alloc
