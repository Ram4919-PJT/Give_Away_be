from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base


class AssistanceApplication(Base):
    __tablename__ = "assistance_applications"

    application_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("receiver_profiles.receiver_id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_requested: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    history: Mapped[list["ApplicationStatusHistory"]] = relationship(back_populates="application", cascade="all, delete-orphan")


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("assistance_applications.application_id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    application: Mapped["AssistanceApplication"] = relationship(back_populates="history")


class NgoItemRequest(Base):
    __tablename__ = "ngo_item_requests"

    request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ngo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ngo_profiles.ngo_id"), nullable=False)
    item_category: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")


class NgoFundRequest(Base):
    __tablename__ = "ngo_fund_requests"

    request_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ngo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ngo_profiles.ngo_id"), nullable=False)
    amount_requested: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
