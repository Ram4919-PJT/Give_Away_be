"""Assistance application review and bank fields.

Consolidates: scripts/ensure_assistance_columns.sql

Revision ID: 009_assistance_review_fields
Revises: 008_receiver_kyc_mobile_otp
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_assistance_review_fields"
down_revision: Union[str, None] = "008_receiver_kyc_mobile_otp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistance_applications",
        sa.Column("amount_approved", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column("assistance_applications", sa.Column("category", sa.String(length=100), nullable=True))
    op.add_column("assistance_applications", sa.Column("expense_breakdown", sa.Text(), nullable=True))
    op.add_column("assistance_applications", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("assistance_applications", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("assistance_applications", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("assistance_applications", sa.Column("reviewed_by_user_id", sa.BigInteger(), nullable=True))
    op.add_column("assistance_applications", sa.Column("payout_status", sa.String(length=50), nullable=True))
    op.add_column(
        "assistance_applications",
        sa.Column("bank_account_holder", sa.String(length=150), nullable=True),
    )
    op.add_column("assistance_applications", sa.Column("bank_name", sa.String(length=150), nullable=True))
    op.add_column("assistance_applications", sa.Column("bank_ifsc", sa.String(length=20), nullable=True))
    op.add_column("assistance_applications", sa.Column("bank_account_last4", sa.String(length=4), nullable=True))
    op.add_column(
        "assistance_applications",
        sa.Column("bank_details_submitted_at", sa.DateTime(), nullable=True),
    )
    op.alter_column(
        "assistance_applications",
        "purpose",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "assistance_applications",
        "purpose",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.drop_column("assistance_applications", "bank_details_submitted_at")
    op.drop_column("assistance_applications", "bank_account_last4")
    op.drop_column("assistance_applications", "bank_ifsc")
    op.drop_column("assistance_applications", "bank_name")
    op.drop_column("assistance_applications", "bank_account_holder")
    op.drop_column("assistance_applications", "payout_status")
    op.drop_column("assistance_applications", "reviewed_by_user_id")
    op.drop_column("assistance_applications", "reviewed_at")
    op.drop_column("assistance_applications", "rejection_reason")
    op.drop_column("assistance_applications", "notes")
    op.drop_column("assistance_applications", "expense_breakdown")
    op.drop_column("assistance_applications", "category")
    op.drop_column("assistance_applications", "amount_approved")
