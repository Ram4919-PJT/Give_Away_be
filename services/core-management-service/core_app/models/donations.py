from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base

if TYPE_CHECKING:
    from core_app.models.item_donation_document import ItemDonationDocument
    from core_app.models.item_donation_request import ItemDonationRequest


class MoneyDonation(Base):
    __tablename__ = "money_donations"

    donation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("donor_profiles.donor_id"), nullable=False)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.program_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="INITIATED")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    guest_mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    guest_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    donated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ItemDonation(Base):
    __tablename__ = "item_donations"

    item_donation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("donor_profiles.donor_id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("item_categories.category_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    item_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pickup_address_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("addresses.address_id"), nullable=False)
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    condition_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_variant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    display_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_pincode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pickup_availability: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_pickup_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    urgency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_request_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    inventory_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("inventory_items.item_id", ondelete="SET NULL"),
        nullable=True,
    )

    pickup_schedules: Mapped[list["PickupSchedule"]] = relationship(
        back_populates="item_donation",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["ItemDonationDocument"]] = relationship(
        back_populates="item_donation",
        cascade="all, delete-orphan",
    )
    requests: Mapped[list["ItemDonationRequest"]] = relationship(
        back_populates="item_donation",
        cascade="all, delete-orphan",
    )


class DonationStatusHistory(Base):
    __tablename__ = "donation_status_history"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    donation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    donation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PickupSchedule(Base):
    __tablename__ = "pickup_schedules"

    pickup_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_donation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("item_donations.item_donation_id", ondelete="CASCADE"), nullable=False)
    pickup_date: Mapped[date] = mapped_column(Date, nullable=False)
    pickup_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED")

    item_donation: Mapped["ItemDonation"] = relationship(back_populates="pickup_schedules")
