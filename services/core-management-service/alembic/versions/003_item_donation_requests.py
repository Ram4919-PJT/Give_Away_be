"""Item donation requests and extended item fields.

Revision ID: 003_item_donation_requests
Revises: 002_item_verification
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_item_donation_requests"
down_revision: Union[str, None] = "002_item_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("item_donations", sa.Column("item_name", sa.String(length=200), nullable=True))
    op.add_column("item_donations", sa.Column("subcategory", sa.String(length=100), nullable=True))
    op.add_column("item_donations", sa.Column("condition", sa.String(length=50), nullable=True))
    op.add_column("item_donations", sa.Column("brand", sa.String(length=100), nullable=True))
    op.add_column("item_donations", sa.Column("model_variant", sa.String(length=100), nullable=True))
    op.add_column("item_donations", sa.Column("category_details", sa.JSON(), nullable=True))
    op.add_column("item_donations", sa.Column("preferences", sa.JSON(), nullable=True))
    op.add_column(
        "item_donations",
        sa.Column("quantity_available", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "item_donations",
        sa.Column("quantity_reserved", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("item_donations", sa.Column("display_city", sa.String(length=100), nullable=True))
    op.add_column("item_donations", sa.Column("display_state", sa.String(length=100), nullable=True))
    op.add_column("item_donations", sa.Column("display_pincode", sa.String(length=20), nullable=True))
    op.add_column("item_donations", sa.Column("pickup_availability", sa.Text(), nullable=True))
    op.add_column("item_donations", sa.Column("preferred_pickup_time", sa.String(length=100), nullable=True))
    op.add_column(
        "item_donations",
        sa.Column("delivery_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("item_donations", sa.Column("urgency", sa.String(length=50), nullable=True))
    op.add_column("item_donations", sa.Column("additional_notes", sa.Text(), nullable=True))
    op.add_column("item_donations", sa.Column("change_request_comment", sa.Text(), nullable=True))

    op.create_table(
        "item_donation_requests",
        sa.Column("request_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_donation_id", sa.BigInteger(), nullable=False),
        sa.Column("receiver_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity_requested", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("donor_response", sa.Text(), nullable=True),
        sa.Column("fulfillment_status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("pickup_or_delivery", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["item_donation_id"],
            ["item_donations.item_donation_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["receiver_id"],
            ["receiver_profiles.receiver_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index("ix_item_donation_requests_item", "item_donation_requests", ["item_donation_id"])
    op.create_index("ix_item_donation_requests_receiver", "item_donation_requests", ["receiver_id"])
    op.create_index("ix_item_donation_requests_status", "item_donation_requests", ["status"])

    op.create_table(
        "item_donation_verification_history",
        sa.Column("history_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_donation_id", sa.BigInteger(), nullable=False),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_donation_id"],
            ["item_donations.item_donation_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("history_id"),
    )

    # Backfill quantity_available from quantity for existing rows
    op.execute(
        "UPDATE item_donations SET quantity_available = quantity "
        "WHERE status IN ('AVAILABLE', 'LISTED') AND quantity_available = 0"
    )
    op.execute(
        "UPDATE item_donations SET status = 'PENDING_VERIFICATION' WHERE status = 'SUBMITTED'"
    )


def downgrade() -> None:
    op.execute("UPDATE item_donations SET status = 'SUBMITTED' WHERE status = 'PENDING_VERIFICATION'")
    op.drop_table("item_donation_verification_history")
    op.drop_index("ix_item_donation_requests_status", table_name="item_donation_requests")
    op.drop_index("ix_item_donation_requests_receiver", table_name="item_donation_requests")
    op.drop_index("ix_item_donation_requests_item", table_name="item_donation_requests")
    op.drop_table("item_donation_requests")
    op.drop_column("item_donations", "change_request_comment")
    op.drop_column("item_donations", "additional_notes")
    op.drop_column("item_donations", "urgency")
    op.drop_column("item_donations", "delivery_available")
    op.drop_column("item_donations", "preferred_pickup_time")
    op.drop_column("item_donations", "pickup_availability")
    op.drop_column("item_donations", "display_pincode")
    op.drop_column("item_donations", "display_state")
    op.drop_column("item_donations", "display_city")
    op.drop_column("item_donations", "quantity_reserved")
    op.drop_column("item_donations", "quantity_available")
    op.drop_column("item_donations", "preferences")
    op.drop_column("item_donations", "category_details")
    op.drop_column("item_donations", "model_variant")
    op.drop_column("item_donations", "brand")
    op.drop_column("item_donations", "condition")
    op.drop_column("item_donations", "subcategory")
    op.drop_column("item_donations", "item_name")
