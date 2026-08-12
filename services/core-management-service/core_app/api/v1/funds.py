from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.models.applications import AssistanceApplication
from core_app.models.funds import Disbursement, FundLedger, FundPool

router = APIRouter(prefix="/funds", tags=["Fund Pools & Ledger"])


class FundPoolCreate(BaseModel):
    pool_name: str
    balance: float = 0.0


class FundLedgerCreate(BaseModel):
    pool_id: int
    transaction_type: str  # CREDIT or DEBIT
    amount: float


class DisbursementCreate(BaseModel):
    application_id: int
    amount: float


@router.get("/pools")
async def list_pools(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FundPool))
    return result.scalars().all()


@router.post("/pools", status_code=status.HTTP_201_CREATED)
async def create_pool(data: FundPoolCreate, db: AsyncSession = Depends(get_db)):
    pool = FundPool(pool_name=data.pool_name, balance=data.balance)
    db.add(pool)
    await db.commit()
    await db.refresh(pool)
    return pool


@router.get("/ledger")
async def list_ledger(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FundLedger))
    return result.scalars().all()


@router.post("/ledger", status_code=status.HTTP_201_CREATED)
async def add_ledger_entry(data: FundLedgerCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FundPool).where(FundPool.pool_id == data.pool_id))
    pool = res.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail=f"Fund pool #{data.pool_id} not found")

    ttype = data.transaction_type.upper()
    if ttype == "CREDIT":
        pool.balance = float(pool.balance) + data.amount
    elif ttype == "DEBIT":
        if float(pool.balance) < data.amount:
            raise HTTPException(status_code=400, detail=f"Insufficient balance in pool (Current: {pool.balance})")
        pool.balance = float(pool.balance) - data.amount

    entry = FundLedger(pool_id=data.pool_id, transaction_type=ttype, amount=data.amount)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/disbursements")
async def list_disbursements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Disbursement))
    return result.scalars().all()


@router.post("/disbursements", status_code=status.HTTP_201_CREATED)
async def create_disbursement(data: DisbursementCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(AssistanceApplication).where(AssistanceApplication.application_id == data.application_id))
    app = res.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application #{data.application_id} not found")

    disb = Disbursement(application_id=data.application_id, amount=data.amount, status="COMPLETED")
    db.add(disb)
    
    app.status = "COMPLETED"
    await db.commit()
    await db.refresh(disb)
    return disb
