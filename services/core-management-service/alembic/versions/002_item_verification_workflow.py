"""Item verification workflow — categories, documents, donation fields.

Revision ID: 002_item_verification
Revises: 64ee791c8f04
Create Date: 2026-08-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_item_verification"
down_revision: Union[str, None] = "64ee791c8f04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "item_categories",
        sa.Column("category_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("category_id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    op.add_column("item_donations", sa.Column("category_id", sa.BigInteger(), nullable=True))
    op.add_column("item_donations", sa.Column("condition_note", sa.String(length=255), nullable=True))
    op.add_column("item_donations", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    op.add_column("item_donations", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("item_donations", sa.Column("reviewed_by_user_id", sa.BigInteger(), nullable=True))
    op.add_column("item_donations", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column("item_donations", sa.Column("inventory_item_id", sa.BigInteger(), nullable=True))

    op.create_index("ix_item_donations_category_id", "item_donations", ["category_id"])
    op.create_foreign_key(
        "fk_item_donations_category_id",
        "item_donations",
        "item_categories",
        ["category_id"],
        ["category_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_item_donations_inventory_item_id",
        "item_donations",
        "inventory_items",
        ["inventory_item_id"],
        ["item_id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "item_donation_documents",
        sa.Column("document_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_donation_id", sa.BigInteger(), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False, server_default="ITEM_PHOTO"),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_donation_id"],
            ["item_donations.item_donation_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index(
        "ix_item_donation_documents_item_donation_id",
        "item_donation_documents",
        ["item_donation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_item_donation_documents_item_donation_id", table_name="item_donation_documents")
    op.drop_table("item_donation_documents")
    op.drop_constraint("fk_item_donations_inventory_item_id", "item_donations", type_="foreignkey")
    op.drop_constraint("fk_item_donations_category_id", "item_donations", type_="foreignkey")
    op.drop_index("ix_item_donations_category_id", table_name="item_donations")
    op.drop_column("item_donations", "inventory_item_id")
    op.drop_column("item_donations", "rejection_reason")
    op.drop_column("item_donations", "reviewed_by_user_id")
    op.drop_column("item_donations", "reviewed_at")
    op.drop_column("item_donations", "submitted_at")
    op.drop_column("item_donations", "condition_note")
    op.drop_column("item_donations", "category_id")
    op.drop_table("item_categories")
