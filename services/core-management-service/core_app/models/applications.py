import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base
from core_app.models.enums import AssistanceRequestStatus, PickupStatus


class AssistanceRequest(Base):
    __tablename__ = "assistance_requests"

    assistance_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    receiver_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AssistanceRequestStatus] = mapped_column(
        Enum(AssistanceRequestStatus, name="assistance_request_status_enum"),
        nullable=False,
        server_default=AssistanceRequestStatus.OPEN.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class NgoAssistanceRequest(Base):
    __tablename__ = "ngo_assistance_requests"

    ngo_assistance_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    ngo_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("programs.program_id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AssistanceRequestStatus] = mapped_column(
        Enum(AssistanceRequestStatus, name="assistance_request_status_enum", create_constraint=False),
        nullable=False,
        server_default=AssistanceRequestStatus.OPEN.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PickupRequest(Base):
    __tablename__ = "pickup_requests"

    pickup_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    donation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donations.donation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("addresses.address_id", ondelete="SET NULL"),
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[PickupStatus] = mapped_column(
        Enum(PickupStatus, name="pickup_status_enum"),
        nullable=False,
        server_default=PickupStatus.REQUESTED.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
