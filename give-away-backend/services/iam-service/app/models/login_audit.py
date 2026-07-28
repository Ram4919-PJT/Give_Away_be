import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import LoginAuditStatus

if TYPE_CHECKING:
    from app.models.user import User


class LoginAudit(Base):
    __tablename__ = "login_audit"

    __table_args__ = (
        Index("ix_login_audit_user_login_time", "user_id", "login_time"),
    )

    audit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    login_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[LoginAuditStatus] = mapped_column(
        Enum(LoginAuditStatus, name="login_audit_status_enum"),
        nullable=False,
        default=LoginAuditStatus.FAILED,
    )

    user: Mapped["User | None"] = relationship(
        back_populates="login_audits",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<LoginAudit("
            f"audit_id={self.audit_id}, "
            f"user_id={self.user_id}, "
            f"status={self.status.value})>"
        )