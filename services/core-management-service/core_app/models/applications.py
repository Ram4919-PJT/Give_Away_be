from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base


class AssistanceApplication(Base):
    __tablename__ = "assistance_applications"

    application_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("receiver_profiles.receiver_id"), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    amount_requested: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    amount_approved: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expense_breakdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payout_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_account_holder: Mapped[str | None] = mapped_column(String(150), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bank_account_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    bank_details_submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payment_destination_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    disbursement_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disbursed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disbursed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action_required_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    history: Mapped[list["ApplicationStatusHistory"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    documents: Mapped[list["AssistanceApplicationDocument"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )


class AssistanceApplicationDocument(Base):
    __tablename__ = "assistance_application_documents"

    document_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("assistance_applications.application_id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    application: Mapped["AssistanceApplication"] = relationship(back_populates="documents")


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("assistance_applications.application_id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    application: Mapped["AssistanceApplication"] = relationship(back_populates="history")


class NgoItemRequest(Base):
    __tablename__ = "ngo_item_requests"

    request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ngo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ngo_profiles.ngo_id"), nullable=False)
    item_category: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), nullable=True)


class NgoFundRequest(Base):
    __tablename__ = "ngo_fund_requests"

    request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ngo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ngo_profiles.ngo_id"), nullable=False)
    amount_requested: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), nullable=True)
