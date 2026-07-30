"""Ensure users.session_version and Wave0 identity columns exist (production recovery).

Production evidence (Railway):
  psycopg2.errors.UndefinedColumn: column users.session_version does not exist

Revision 20260730_0023 adds session_version in the same transaction as the
unique platform_owner index. If that migration failed (or the DB was stamped
without applying DDL), the column can be missing while alembic_version is at
or past 0023/0024. This revision is idempotent and only adds missing pieces.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260730_0025_ensure_session_version"
down_revision = "20260730_0024_security_wave0_identity"
branch_labels = None
depends_on = None


def _users_columns(bind) -> set[str]:
    insp = sa.inspect(bind)
    if "users" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("users")}


def upgrade() -> None:
    bind = op.get_bind()
    cols = _users_columns(bind)
    if not cols:
        return

    # 1) session_version — required by JWT / get_current_user
    # Single ADD with DEFAULT backfills existing rows on PostgreSQL and SQLite.
    if "session_version" not in cols:
        op.add_column(
            "users",
            sa.Column(
                "session_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
        op.execute(sa.text("UPDATE users SET session_version = 0 WHERE session_version IS NULL"))
        cols = _users_columns(bind)

    # 2) Wave0 identity columns (safe no-ops if already present)
    additions = [
        ("failed_login_attempts", sa.Integer(), "0", False),
        ("locked_until", sa.DateTime(), None, True),
        ("token_version", sa.Integer(), "0", False),
        ("password_changed_at", sa.DateTime(), None, True),
        ("last_login_at", sa.DateTime(), None, True),
        ("mfa_secret", sa.String(), None, True),
        ("mfa_enabled", sa.Boolean(), "false", False),
    ]
    for name, col_type, server_default, nullable in additions:
        if name in cols:
            continue
        kwargs: dict = {"nullable": nullable}
        if server_default is not None:
            kwargs["server_default"] = sa.text(server_default)
            kwargs["nullable"] = False
        op.add_column("users", sa.Column(name, col_type, **kwargs))
        if server_default is not None:
            op.execute(
                sa.text(f"UPDATE users SET {name} = {server_default} WHERE {name} IS NULL")
            )

    # Refresh tokens / denylist tables if missing (0024 may have been stamped only)
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "refresh_tokens" not in tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("jti", sa.String(64), nullable=False, unique=True),
            sa.Column("family_id", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("replaced_by_jti", sa.String(64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
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
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("reason", sa.String(64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_access_token_denylist_expires_at", "access_token_denylist", ["expires_at"]
        )
        op.create_index("ix_access_token_denylist_jti", "access_token_denylist", ["jti"])


def downgrade() -> None:
    # Non-destructive downgrade: keep columns (production safety).
    pass
