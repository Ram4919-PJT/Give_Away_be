"""Add Razorpay payment fields to money donations.

Revision ID: 005_razorpay_payments
Revises: 004_location_geography
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_razorpay_payments"
down_revision: Union[str, None] = "004_location_geography"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("money_donations", sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"))
    op.add_column("money_donations", sa.Column("razorpay_order_id", sa.String(length=100), nullable=True))
    op.add_column("money_donations", sa.Column("razorpay_payment_id", sa.String(length=100), nullable=True))
    op.add_column("money_donations", sa.Column("payment_method", sa.String(length=50), nullable=True))
    op.add_column("money_donations", sa.Column("guest_mobile", sa.String(length=20), nullable=True))
    op.add_column("money_donations", sa.Column("guest_name", sa.String(length=120), nullable=True))
    op.add_column("money_donations", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column("money_donations", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_money_donations_razorpay_order_id", "money_donations", ["razorpay_order_id"], unique=True)
    op.create_index("ix_money_donations_razorpay_payment_id", "money_donations", ["razorpay_payment_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_money_donations_razorpay_payment_id", table_name="money_donations")
    op.drop_index("ix_money_donations_razorpay_order_id", table_name="money_donations")
    op.drop_column("money_donations", "paid_at")
    op.drop_column("money_donations", "failure_reason")
    op.drop_column("money_donations", "guest_name")
    op.drop_column("money_donations", "guest_mobile")
    op.drop_column("money_donations", "payment_method")
    op.drop_column("money_donations", "razorpay_payment_id")
    op.drop_column("money_donations", "razorpay_order_id")
    op.drop_column("money_donations", "currency")
