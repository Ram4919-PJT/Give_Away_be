"""Assistance application documents and action-required support.

Revision ID: 012_assistance_documents
Revises: 011_ngo_program_extensions
Create Date: 2026-08-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_assistance_documents"
down_revision: Union[str, None] = "011_ngo_program_extensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assistance_applications",
        sa.Column("action_required_reason", sa.Text(), nullable=True),
    )
    op.create_table(
        "assistance_application_documents",
        sa.Column("document_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "application_id",
            sa.BigInteger(),
            sa.ForeignKey("assistance_applications.application_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index(
        "idx_assistance_app_documents_application_id",
        "assistance_application_documents",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_assistance_app_documents_application_id", table_name="assistance_application_documents")
    op.drop_table("assistance_application_documents")
    op.drop_column("assistance_applications", "action_required_reason")
