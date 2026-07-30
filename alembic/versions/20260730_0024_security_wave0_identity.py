"""Security Wave 0 — identity columns, refresh tokens, access denylist."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260730_0024_security_wave0_identity"
down_revision = "20260730_0023_single_platform_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("users")} if "users" in insp.get_table_names() else set()

    additions = [
        ("failed_login_attempts", sa.Integer(), sa.text("0")),
        ("locked_until", sa.DateTime(), None),
        ("token_version", sa.Integer(), sa.text("0")),
        ("password_changed_at", sa.DateTime(), None),
        ("last_login_at", sa.DateTime(), None),
        ("mfa_secret", sa.String(), None),
        ("mfa_enabled", sa.Boolean(), sa.text("false")),
    ]
    for name, col_type, server_default in additions:
        if name in cols:
            continue
        kwargs = {"nullable": False} if server_default is not None and name != "mfa_secret" else {"nullable": True}
        if name in ("failed_login_attempts", "token_version", "mfa_enabled"):
            kwargs["nullable"] = False
            kwargs["server_default"] = server_default
        elif server_default is not None:
            kwargs["server_default"] = server_default
        op.add_column("users", sa.Column(name, col_type, **kwargs))

    tables = set(insp.get_table_names())
    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("jti", sa.String(64), nullable=False, unique=True),
            sa.Column("family_id", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("replaced_by_jti", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("user_agent", sa.String(512), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
        )
        op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
        op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
        op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    if "access_token_denylist" not in tables:
        op.create_table(
            "access_token_denylist",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("jti", sa.String(64), nullable=False, unique=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("reason", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_access_token_denylist_expires_at", "access_token_denylist", ["expires_at"])
        op.create_index("ix_access_token_denylist_jti", "access_token_denylist", ["jti"])


def downgrade() -> None:
    op.drop_table("access_token_denylist")
    op.drop_table("refresh_tokens")
    for col in (
        "mfa_enabled",
        "mfa_secret",
        "last_login_at",
        "password_changed_at",
        "token_version",
        "locked_until",
        "failed_login_attempts",
    ):
        try:
            op.drop_column("users", col)
        except Exception:
            pass
