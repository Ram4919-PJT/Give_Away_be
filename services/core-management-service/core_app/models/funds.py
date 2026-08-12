from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base


class FundPool(Base):
    __tablename__ = "fund_pools"

    pool_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pool_name: Mapped[str] = mapped_column(String(150), nullable=False)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.00)

    ledger_entries: Mapped[list["FundLedger"]] = relationship(back_populates="pool", cascade="all, delete-orphan")


class FundLedger(Base):
    __tablename__ = "fund_ledger"

    ledger_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pool_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fund_pools.pool_id"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    pool: Mapped["FundPool"] = relationship(back_populates="ledger_entries")


class Disbursement(Base):
    __tablename__ = "disbursements"

    disbursement_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("assistance_applications.application_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    disbursed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[str] = mapped_column(String(50), default="COMPLETED")


class Allocation(Base):
    __tablename__ = "allocations"

    allocation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ngo_request_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ngo_item_requests.request_id"), nullable=False)
    item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("inventory_items.item_id"), nullable=False)
    quantity_allocated: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
