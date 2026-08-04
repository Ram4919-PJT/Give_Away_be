import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base
from core_app.models.enums import DonationStatus, DonationType


class Donation(Base):
    __tablename__ = "donations"

    donation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    donor_user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    donation_type: Mapped[DonationType] = mapped_column(
        Enum(DonationType, name="donation_type_enum"),
        nullable=False,
    )
    status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus, name="donation_status_enum"),
        nullable=False,
        server_default=DonationStatus.DRAFT.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    money_detail: Mapped["MoneyDonationDetail | None"] = relationship(
        back_populates="donation", uselist=False
    )
    item_detail: Mapped["ItemDonationDetail | None"] = relationship(
        back_populates="donation", uselist=False
    )
    items: Mapped[list["DonationItem"]] = relationship(back_populates="donation")
    status_history: Mapped[list["DonationStatusHistory"]] = relationship(
        back_populates="donation"
    )


class MoneyDonationDetail(Base):
    __tablename__ = "money_donation_details"

    money_donation_detail_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    donation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donations.donation_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    payment_reference: Mapped[str | None] = mapped_column(String(100))

    donation: Mapped["Donation"] = relationship(back_populates="money_detail")


class ItemDonationDetail(Base):
    __tablename__ = "item_donation_details"

    item_donation_detail_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    donation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("donations.donation_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    pickup_address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("addresses.address_id", ondelete="SET NULL"),
    )
    estimated_value: Mapped[float | None] = mapped_column(Numeric(14, 2))

    donation: Mapped["Donation"] = relationship(back_populates="item_detail")


class DonationItem(Base):
    __tablename__ = "donation_items"

    donation_item_id: Mapped[uuid.UUID] = mapped_column(
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
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    unit: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    donation: Mapped["Donation"] = relationship(back_populates="items")


class DonationStatusHistory(Base):
    __tablename__ = "donation_status_history"

    history_id: Mapped[uuid.UUID] = mapped_column(
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
    from_status: Mapped[DonationStatus | None] = mapped_column(
        Enum(DonationStatus, name="donation_status_enum", create_constraint=False)
    )
    to_status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus, name="donation_status_enum", create_constraint=False),
        nullable=False,
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    comment: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    donation: Mapped["Donation"] = relationship(back_populates="status_history")
