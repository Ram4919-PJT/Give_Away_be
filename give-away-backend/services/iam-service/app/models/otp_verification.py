import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import OtpPurpose, OtpVerificationStatus

if TYPE_CHECKING:
    from app.models.user import User


class OtpVerification(Base):
    __tablename__ = "otp_verifications"

    __table_args__ = (
        Index(
            "ix_otp_user_purpose_status",
            "user_id",
            "purpose",
            "verified_status",
        ),
    )

    otp_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    otp_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    purpose: Mapped[OtpPurpose] = mapped_column(
        Enum(OtpPurpose, name="otp_purpose_enum"),
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified_status: Mapped[OtpVerifiedStatus] = mapped_column(
        Enum(
            OtpVerifiedStatus,
            name="otp_verified_status_enum",
        ),
        nullable=False,
        default=OtpVerifiedStatus.PENDING,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
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
            f"purpose={self.purpose}, "
            f"status={self.verified_status})>"
        )