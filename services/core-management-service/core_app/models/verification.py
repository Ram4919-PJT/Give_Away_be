from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base


class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    documents: Mapped[list["VerificationDocument"]] = relationship(back_populates="request", cascade="all, delete-orphan")
    history: Mapped[list["VerificationStatusHistory"]] = relationship(back_populates="request", cascade="all, delete-orphan")
    rejection_reasons: Mapped[list["RejectionReason"]] = relationship(back_populates="request", cascade="all, delete-orphan")


class VerificationDocument(Base):
    __tablename__ = "verification_documents"

    document_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("verification_requests.request_id", ondelete="CASCADE"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    request: Mapped["VerificationRequest"] = relationship(back_populates="documents")


class VerificationStatusHistory(Base):
    __tablename__ = "verification_status_history"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("verification_requests.request_id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    request: Mapped["VerificationRequest"] = relationship(back_populates="history")


class RejectionReason(Base):
    __tablename__ = "rejection_reasons"

    reason_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("verification_requests.request_id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    request: Mapped["VerificationRequest"] = relationship(back_populates="rejection_reasons")
