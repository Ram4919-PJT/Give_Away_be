from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base


class RecurringGift(Base):
    """Ongoing scheduled gifts from a donor toward a program/cause."""

    __tablename__ = "recurring_gifts"

    gift_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("donor_profiles.donor_id"), nullable=False)
    program_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("programs.program_id"), nullable=False)
    organization_name: Mapped[str] = mapped_column(String(150), nullable=False, default="Aja Abayahastham")
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False, default="MONTHLY")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payments_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
