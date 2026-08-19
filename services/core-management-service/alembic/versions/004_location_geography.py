"""Add geographic coordinates for addresses and donor discovery location.

Revision ID: 004_location_geography
Revises: 003_item_donation_requests
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_location_geography"
down_revision: Union[str, None] = "003_item_donation_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("addresses", sa.Column("latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("addresses", sa.Column("longitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("addresses", sa.Column("country", sa.String(length=100), nullable=True))

    op.add_column("donor_profiles", sa.Column("location_latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("donor_profiles", sa.Column("location_longitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("donor_profiles", sa.Column("location_city", sa.String(length=100), nullable=True))
    op.add_column("donor_profiles", sa.Column("location_state", sa.String(length=100), nullable=True))
    op.add_column("donor_profiles", sa.Column("location_country", sa.String(length=100), nullable=True))
    op.add_column(
        "donor_profiles",
        sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_addresses_lat_lng", "addresses", ["latitude", "longitude"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_addresses_lat_lng", table_name="addresses")
    op.drop_column("donor_profiles", "location_updated_at")
    op.drop_column("donor_profiles", "location_country")
    op.drop_column("donor_profiles", "location_state")
    op.drop_column("donor_profiles", "location_city")
    op.drop_column("donor_profiles", "location_longitude")
    op.drop_column("donor_profiles", "location_latitude")
    op.drop_column("addresses", "country")
    op.drop_column("addresses", "longitude")
    op.drop_column("addresses", "latitude")
