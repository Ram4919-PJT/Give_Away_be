from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base

if TYPE_CHECKING:
    from core_app.models.donations import ItemDonation
    from core_app.models.profiles import ReceiverProfile


class ItemDonationRequest(Base):
    __tablename__ = "item_donation_requests"

    request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_donation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("item_donations.item_donation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiver_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("receiver_profiles.receiver_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    donor_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    fulfillment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    pickup_or_delivery: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    item_donation: Mapped["ItemDonation"] = relationship(back_populates="requests")
    receiver: Mapped["ReceiverProfile"] = relationship()


class ItemDonationVerificationHistory(Base):
    __tablename__ = "item_donation_verification_history"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_donation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("item_donations.item_donation_id", ondelete="CASCADE"),
        nullable=False,
    )
    admin_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
