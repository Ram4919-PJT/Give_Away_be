"""Allow null submitted_at on draft verification requests.

Revision ID: 013_verification_submitted_at_nullable
Revises: 012_assistance_application_documents
Create Date: 2026-08-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_nullable_submitted_at"
down_revision: Union[str, None] = "012_assistance_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Draft KYC rows should not have a submission timestamp until the user submits.
    op.execute(
        """
        UPDATE verification_requests
        SET submitted_at = NULL
        WHERE status IN ('DRAFT', 'KYC_IN_PROGRESS')
          AND submitted_at IS NOT NULL
        """
    )
    op.alter_column(
        "verification_requests",
        "submitted_at",
        existing_type=sa.DateTime(),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE verification_requests
        SET submitted_at = COALESCE(submitted_at, created_at, NOW())
        WHERE submitted_at IS NULL
        """
    )
    op.alter_column(
        "verification_requests",
        "submitted_at",
        existing_type=sa.DateTime(),
        nullable=False,
        server_default=sa.text("now()"),
    )
