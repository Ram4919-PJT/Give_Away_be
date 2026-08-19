from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base


class Address(Base):
    __tablename__ = "addresses"

    address_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    line1: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)


class DonorProfile(Base):
    __tablename__ = "donor_profiles"

    donor_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    address_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("addresses.address_id"))
    location_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    location_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preferences: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ReceiverProfile(Base):
    __tablename__ = "receiver_profiles"

    receiver_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    address_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("addresses.address_id"))
    verification_status: Mapped[str] = mapped_column(String(50), default="REGISTERED")


class NgoProfile(Base):
    __tablename__ = "ngo_profiles"

    ngo_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    ngo_name: Mapped[str] = mapped_column(String(150), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    contact_person: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    address_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("addresses.address_id"))
    verification_status: Mapped[str] = mapped_column(String(50), default="REGISTERED")

    beneficiaries: Mapped[list["Beneficiary"]] = relationship(back_populates="ngo_profile", cascade="all, delete-orphan")


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    beneficiary_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ngo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ngo_profiles.ngo_id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)

    ngo_profile: Mapped["NgoProfile"] = relationship(back_populates="beneficiaries")


class Program(Base):
    __tablename__ = "programs"

    program_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    program_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    ngo_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("ngo_profiles.ngo_id"), nullable=True)
    goal_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount_raised: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True, default=0)
    donors_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
