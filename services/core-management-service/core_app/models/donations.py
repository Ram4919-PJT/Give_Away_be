from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base


class MoneyDonation(Base):
    __tablename__ = "money_donations"

    donation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("donor_profiles.donor_id"), nullable=False)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.program_id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="INITIATED")
    donated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ItemDonation(Base):
    __tablename__ = "item_donations"

    item_donation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("donor_profiles.donor_id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    pickup_address_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("addresses.address_id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="LISTED")

    pickup_schedules: Mapped[list["PickupSchedule"]] = relationship(back_populates="item_donation", cascade="all, delete-orphan")


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
