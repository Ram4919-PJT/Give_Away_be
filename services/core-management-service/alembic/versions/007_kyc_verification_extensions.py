"""KYC verification extensions — columns, indexes, audit log.

Consolidates: scripts/ensure_kyc_verification_columns.sql

Revision ID: 007_kyc_verification_extensions
Revises: 006_donor_preferences
Create Date: 2026-08-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_kyc_verification_extensions"
down_revision: Union[str, None] = "006_donor_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("verification_requests", sa.Column("reference_code", sa.String(length=32), nullable=True))
    op.add_column("verification_requests", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("verification_requests", sa.Column("reviewed_by", sa.BigInteger(), nullable=True))
    op.add_column("verification_requests", sa.Column("risk_level", sa.String(length=32), nullable=True))
    op.add_column(
        "verification_requests",
        sa.Column("risk_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "verification_requests",
        sa.Column("consent_given", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.add_column("verification_requests", sa.Column("consent_version", sa.String(length=32), nullable=True))
    op.add_column("verification_requests", sa.Column("consent_timestamp", sa.DateTime(), nullable=True))
    op.add_column(
        "verification_requests",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "verification_requests",
        sa.Column("current_step", sa.BigInteger(), nullable=True, server_default=sa.text("1")),
    )
    op.add_column(
        "verification_requests",
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )
    op.add_column(
        "verification_requests",
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )

    op.add_column("verification_documents", sa.Column("storage_key", sa.String(length=512), nullable=True))
    op.add_column("verification_documents", sa.Column("original_filename", sa.String(length=255), nullable=True))
    op.add_column("verification_documents", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("verification_documents", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column(
        "verification_documents",
        sa.Column(
            "verification_status",
            sa.String(length=50),
            nullable=True,
            server_default=sa.text("'UPLOADED'"),
        ),
    )
    op.add_column("verification_documents", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.add_column(
        "verification_documents",
        sa.Column(
            "verification_source",
            sa.String(length=32),
            nullable=True,
            server_default=sa.text("'MANUAL'"),
        ),
    )
    op.add_column(
        "verification_documents",
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("verification_documents", sa.Column("verified_at", sa.DateTime(), nullable=True))
    op.add_column("verification_documents", sa.Column("verified_by", sa.BigInteger(), nullable=True))

    op.add_column("verification_status_history", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("verification_status_history", sa.Column("changed_by", sa.BigInteger(), nullable=True))

    op.create_index(
        "idx_verification_requests_reference_code",
        "verification_requests",
        ["reference_code"],
        unique=True,
        postgresql_where=sa.text("reference_code IS NOT NULL"),
    )
    op.create_index("idx_verification_requests_user_id", "verification_requests", ["user_id"])
    op.create_index("idx_verification_requests_status", "verification_requests", ["status"])

    op.create_table(
        "verification_audit_log",
        sa.Column("audit_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=False),
        sa.Column("request_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("old_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("idx_verification_audit_request", "verification_audit_log", ["request_id"])

    op.execute(
        """
        UPDATE verification_documents
        SET storage_key = file_url
        WHERE storage_key IS NULL AND file_url IS NOT NULL AND file_url <> ''
        """
    )


def downgrade() -> None:
    op.drop_index("idx_verification_audit_request", table_name="verification_audit_log")
    op.drop_table("verification_audit_log")

    op.drop_index("idx_verification_requests_status", table_name="verification_requests")
    op.drop_index("idx_verification_requests_user_id", table_name="verification_requests")
    op.drop_index("idx_verification_requests_reference_code", table_name="verification_requests")

    op.drop_column("verification_status_history", "changed_by")
    op.drop_column("verification_status_history", "note")

    op.drop_column("verification_documents", "verified_by")
    op.drop_column("verification_documents", "verified_at")
    op.drop_column("verification_documents", "metadata_json")
    op.drop_column("verification_documents", "verification_source")
    op.drop_column("verification_documents", "rejection_reason")
    op.drop_column("verification_documents", "verification_status")
    op.drop_column("verification_documents", "size_bytes")
    op.drop_column("verification_documents", "mime_type")
    op.drop_column("verification_documents", "original_filename")
    op.drop_column("verification_documents", "storage_key")

    op.drop_column("verification_requests", "updated_at")
    op.drop_column("verification_requests", "created_at")
    op.drop_column("verification_requests", "current_step")
    op.drop_column("verification_requests", "payload")
    op.drop_column("verification_requests", "consent_timestamp")
    op.drop_column("verification_requests", "consent_version")
    op.drop_column("verification_requests", "consent_given")
    op.drop_column("verification_requests", "risk_flags")
    op.drop_column("verification_requests", "risk_level")
    op.drop_column("verification_requests", "reviewed_by")
    op.drop_column("verification_requests", "reviewed_at")
    op.drop_column("verification_requests", "reference_code")
