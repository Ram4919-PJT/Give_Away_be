import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base
from core_app.models.enums import FundDisbursementStatus, FundLedgerEntryType


class FundPool(Base):
    __tablename__ = "fund_pools"

    fund_pool_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    balance: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, server_default=text("0"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    ledger_entries: Mapped[list["FundLedgerEntry"]] = relationship(back_populates="fund_pool")
    disbursements: Mapped[list["FundDisbursement"]] = relationship(back_populates="fund_pool")


class FundLedgerEntry(Base):
    __tablename__ = "fund_ledger_entries"

    ledger_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    fund_pool_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fund_pools.fund_pool_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    donation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donations.donation_id", ondelete="SET NULL"),
    )
    entry_type: Mapped[FundLedgerEntryType] = mapped_column(
        Enum(FundLedgerEntryType, name="fund_ledger_entry_type_enum"),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    fund_pool: Mapped["FundPool"] = relationship(back_populates="ledger_entries")


class FundDisbursement(Base):
    __tablename__ = "fund_disbursements"

    disbursement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    fund_pool_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fund_pools.fund_pool_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    beneficiary_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[FundDisbursementStatus] = mapped_column(
        Enum(FundDisbursementStatus, name="fund_disbursement_status_enum"),
        nullable=False,
        server_default=FundDisbursementStatus.PENDING.value,
        index=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    fund_pool: Mapped["FundPool"] = relationship(back_populates="disbursements")
    allocations: Mapped[list["FundAllocation"]] = relationship(back_populates="disbursement")


class FundAllocation(Base):
    __tablename__ = "fund_allocations"

    allocation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    disbursement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fund_disbursements.disbursement_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assistance_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assistance_requests.assistance_request_id", ondelete="SET NULL"),
    )
    allocated_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    disbursement: Mapped["FundDisbursement"] = relationship(back_populates="allocations")
