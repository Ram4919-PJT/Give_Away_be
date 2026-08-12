from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class OtpVerification(Base):
    __tablename__ = "otp_verifications"

    otp_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    otp_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    verified_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )

    user: Mapped["User"] = relationship(
        back_populates="otp_verifications",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<OtpVerification("
            f"otp_id={self.otp_id}, "
            f"user_id={self.user_id}, "
            f"purpose='{self.purpose}', "
            f"status='{self.verified_status}')>"
        )