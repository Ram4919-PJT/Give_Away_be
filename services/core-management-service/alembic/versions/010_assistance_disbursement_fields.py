"""Assistance disbursement tracking fields.

Consolidates: scripts/ensure_assistance_disbursement_columns.sql

Revision ID: 010_assistance_disbursement
Revises: 009_assistance_review_and_bank_fields
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_assistance_disbursement"
down_revision: Union[str, None] = "009_assistance_review_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistance_applications",
        sa.Column("disbursement_reference", sa.String(length=100), nullable=True),
    )
    op.add_column("assistance_applications", sa.Column("disbursed_at", sa.DateTime(), nullable=True))
    op.add_column("assistance_applications", sa.Column("disbursed_by", sa.BigInteger(), nullable=True))
    op.add_column(
        "assistance_applications",
        sa.Column("payment_destination_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assistance_applications", "payment_destination_type")
    op.drop_column("assistance_applications", "disbursed_by")
    op.drop_column("assistance_applications", "disbursed_at")
    op.drop_column("assistance_applications", "disbursement_reference")
