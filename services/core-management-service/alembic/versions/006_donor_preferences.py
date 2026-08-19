"""Add donor profile preferences JSON for settings.

Revision ID: 006_donor_preferences
Revises: 005_razorpay_payments
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_donor_preferences"
down_revision: Union[str, None] = "005_razorpay_payments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("donor_profiles", sa.Column("preferences", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("donor_profiles", "preferences")
