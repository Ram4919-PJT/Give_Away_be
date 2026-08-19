"""NGO program ownership and request timestamps.

Consolidates: scripts/ensure_ngo_dashboard_columns.sql

Revision ID: 011_ngo_program_extensions
Revises: 010_assistance_disbursement_fields
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_ngo_program_extensions"
down_revision: Union[str, None] = "010_assistance_disbursement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("programs", sa.Column("ngo_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_programs_ngo_id",
        "programs",
        "ngo_profiles",
        ["ngo_id"],
        ["ngo_id"],
    )
    op.add_column("programs", sa.Column("goal_amount", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column(
        "programs",
        sa.Column("amount_raised", sa.Numeric(precision=12, scale=2), nullable=True, server_default=sa.text("0")),
    )
    op.add_column(
        "programs",
        sa.Column("donors_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
    )
    op.add_column("programs", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("programs", sa.Column("start_date", sa.DateTime(), nullable=True))
    op.add_column("programs", sa.Column("end_date", sa.DateTime(), nullable=True))
    op.add_column(
        "programs",
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )

    op.add_column(
        "ngo_item_requests",
        sa.Column("submitted_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )
    op.add_column(
        "ngo_fund_requests",
        sa.Column("submitted_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_column("ngo_fund_requests", "submitted_at")
    op.drop_column("ngo_item_requests", "submitted_at")

    op.drop_column("programs", "created_at")
    op.drop_column("programs", "end_date")
    op.drop_column("programs", "start_date")
    op.drop_column("programs", "image_url")
    op.drop_column("programs", "donors_count")
    op.drop_column("programs", "amount_raised")
    op.drop_column("programs", "goal_amount")
    op.drop_constraint("fk_programs_ngo_id", "programs", type_="foreignkey")
    op.drop_column("programs", "ngo_id")
