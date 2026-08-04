import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base
from core_app.models.enums import ProfileStatus, ProgramStatus


class Address(Base):
    __tablename__ = "addresses"

    address_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, server_default="India")
    is_primary: Mapped[bool] = mapped_column(nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DonorProfile(Base):
    __tablename__ = "donor_profiles"

    donor_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, unique=True, index=True
    )
    organization_name: Mapped[str | None] = mapped_column(String(255))
    pan_number: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[ProfileStatus] = mapped_column(
        Enum(ProfileStatus, name="profile_status_enum"),
        nullable=False,
        server_default=ProfileStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ReceiverProfile(Base):
    __tablename__ = "receiver_profiles"

    receiver_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, unique=True, index=True
    )
    household_size: Mapped[int | None] = mapped_column()
    monthly_income: Mapped[float | None] = mapped_column(Numeric(12, 2))
    status: Mapped[ProfileStatus] = mapped_column(
        Enum(ProfileStatus, name="profile_status_enum", create_constraint=False),
        nullable=False,
        server_default=ProfileStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    beneficiaries: Mapped[list["Beneficiary"]] = relationship(back_populates="receiver_profile")


class NgoProfile(Base):
    __tablename__ = "ngo_profiles"

    ngo_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, unique=True, index=True
    )
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    focus_area: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ProfileStatus] = mapped_column(
        Enum(ProfileStatus, name="profile_status_enum", create_constraint=False),
        nullable=False,
        server_default=ProfileStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    programs: Mapped[list["Program"]] = relationship(back_populates="ngo_profile")


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    beneficiary_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    receiver_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("receiver_profiles.receiver_profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int | None] = mapped_column()
    relationship_type: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    receiver_profile: Mapped["ReceiverProfile"] = relationship(back_populates="beneficiaries")


class Program(Base):
    __tablename__ = "programs"

    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    ngo_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ngo_profiles.ngo_profile_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProgramStatus] = mapped_column(
        Enum(ProgramStatus, name="program_status_enum"),
        nullable=False,
        server_default=ProgramStatus.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    ngo_profile: Mapped["NgoProfile"] = relationship(back_populates="programs")
