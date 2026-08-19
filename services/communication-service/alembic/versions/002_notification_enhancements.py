"""Notification enhancements — type, entity refs, indexes.

Revision ID: 002_notification_enhancements
Revises: 24de5f26e874
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_notification_enhancements"
down_revision: Union[str, None] = "24de5f26e874"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("notification_type", sa.String(length=50), nullable=False, server_default="ACCOUNT"),
    )
    op.add_column("notifications", sa.Column("related_entity_type", sa.String(length=50), nullable=True))
    op.add_column("notifications", sa.Column("related_entity_id", sa.BigInteger(), nullable=True))
    op.add_column("notifications", sa.Column("action_url", sa.String(length=500), nullable=True))
    op.add_column("notifications", sa.Column("read_at", sa.DateTime(), nullable=True))
    op.add_column(
        "notifications",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_user_status", "notifications", ["user_id", "status"])
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_index("ix_notifications_user_status", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_column("notifications", "updated_at")
    op.drop_column("notifications", "read_at")
    op.drop_column("notifications", "action_url")
    op.drop_column("notifications", "related_entity_id")
    op.drop_column("notifications", "related_entity_type")
    op.drop_column("notifications", "notification_type")
