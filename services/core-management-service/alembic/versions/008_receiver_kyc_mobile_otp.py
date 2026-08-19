"""Receiver KYC mobile OTP table.

Consolidates: scripts/ensure_receiver_kyc_phase2.sql

Revision ID: 008_receiver_kyc_mobile_otp
Revises: 007_kyc_verification_extensions
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_receiver_kyc_mobile_otp"
down_revision: Union[str, None] = "007_kyc_verification_extensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kyc_mobile_otp",
        sa.Column("otp_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("mobile", sa.String(length=20), nullable=False),
        sa.Column("otp_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("otp_id"),
    )
    op.create_index("idx_kyc_mobile_otp_user_id", "kyc_mobile_otp", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_kyc_mobile_otp_user_id", table_name="kyc_mobile_otp")
    op.drop_table("kyc_mobile_otp")
