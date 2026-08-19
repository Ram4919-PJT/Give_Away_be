from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base

if TYPE_CHECKING:
    from core_app.models.donations import ItemDonation


class ItemDonationDocument(Base):
    __tablename__ = "item_donation_documents"

    document_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_donation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("item_donations.item_donation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="ITEM_PHOTO")
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    item_donation: Mapped["ItemDonation"] = relationship(back_populates="documents")
