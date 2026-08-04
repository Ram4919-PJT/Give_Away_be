"""Initial IAM schema

Revision ID: 001
Revises:
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    role_name_enum = sa.Enum(
        "DONOR",
        "RECEIVER",
        "NGO",
        "SUPER_ADMIN",
        name="role_name_enum",
    )
    user_status_enum = sa.Enum(
        "ACTIVE",
        "INACTIVE",
        "SUSPENDED",
        name="user_status_enum",
    )
    login_audit_status_enum = sa.Enum(
        "SUCCESS",
        "FAILED",
        name="login_audit_status_enum",
    )
    otp_purpose_enum = sa.Enum(
        "REGISTRATION",
        "LOGIN",
        "PASSWORD_RESET",
        "MOBILE_VERIFICATION",
        name="otp_purpose_enum",
    )
    otp_verified_status_enum = sa.Enum(
        "PENDING",
        "VERIFIED",
        "EXPIRED",
        name="otp_verified_status_enum",
    )

    op.create_table(
        "roles",
        sa.Column(
            "role_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("role_name", role_name_enum, nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("role_id"),
        sa.UniqueConstraint("role_name"),
    )

    op.create_table(
        "users",
        sa.Column(
            "user_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("mobile", sa.String(length=15), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            user_status_enum,
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("mobile"),
    )
    op.create_index("ix_users_role_id", "users", ["role_id"])
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index(
        "ix_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "token_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index(
        "ix_refresh_tokens_user_expires", "refresh_tokens", ["user_id", "expires_at"]
    )

    op.create_table(
        "login_audit",
        sa.Column(
            "audit_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "login_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("status", login_audit_status_enum, nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_login_audit_user_id", "login_audit", ["user_id"])
    op.create_index(
        "ix_login_audit_user_login_time", "login_audit", ["user_id", "login_time"]
    )

    op.create_table(
        "otp_verifications",
        sa.Column(
            "otp_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("otp_code", sa.String(length=10), nullable=False),
        sa.Column("purpose", otp_purpose_enum, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "verified_status",
            otp_verified_status_enum,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("otp_id"),
    )
    op.create_index("ix_otp_verifications_user_id", "otp_verifications", ["user_id"])
    op.create_index("ix_otp_verifications_purpose", "otp_verifications", ["purpose"])
    op.create_index(
        "ix_otp_verifications_verified_status", "otp_verifications", ["verified_status"]
    )
    op.create_index(
        "ix_otp_user_purpose_status",
        "otp_verifications",
        ["user_id", "purpose", "verified_status"],
    )


def downgrade() -> None:
    op.drop_table("otp_verifications")
    op.drop_table("login_audit")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("roles")

    bind = op.get_bind()
    sa.Enum(name="otp_verified_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="otp_purpose_enum").drop(bind, checkfirst=True)
    sa.Enum(name="login_audit_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="user_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="role_name_enum").drop(bind, checkfirst=True)
