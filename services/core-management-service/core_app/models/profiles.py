from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base


class Address(Base):
    __tablename__ = "addresses"

    address_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    line1: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    pincode: Mapped[str] = mapped_column(String(20), nullable=False)


class DonorProfile(Base):
    __tablename__ = "donor_profiles"

    donor_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    address_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("addresses.address_id"))


class ReceiverProfile(Base):
    __tablename__ = "receiver_profiles"

    receiver_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    address_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("addresses.address_id"))
    verification_status: Mapped[str] = mapped_column(String(50), default="REGISTERED")


class NgoProfile(Base):
    __tablename__ = "ngo_profiles"

    ngo_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), unique=True, nullable=False)
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
