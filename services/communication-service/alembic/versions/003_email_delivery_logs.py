"""Email delivery audit log table.

Consolidates: scripts/ensure_email_delivery_table.sql

Revision ID: 003_email_delivery_logs
Revises: 002_notification_enhancements
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_email_delivery_logs"
down_revision: Union[str, None] = "002_notification_enhancements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_delivery_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column(
            "notification_type",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'ACCOUNT'"),
        ),
        sa.Column("event_type", sa.String(length=80), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column("related_entity_type", sa.String(length=50), nullable=True),
        sa.Column("related_entity_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("idx_email_delivery_logs_user_id", "email_delivery_logs", ["user_id"])
    op.create_index("idx_email_delivery_logs_status", "email_delivery_logs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_email_delivery_logs_status", table_name="email_delivery_logs")
    op.drop_index("idx_email_delivery_logs_user_id", table_name="email_delivery_logs")
    op.drop_table("email_delivery_logs")
