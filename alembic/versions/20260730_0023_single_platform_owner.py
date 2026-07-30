"""Enforce a single platform owner at the database boundary."""

from alembic import op
import sqlalchemy as sa

revision = "20260730_0023_single_platform_owner"
down_revision = "20260629_0022_nurse_handoff_fields"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_users_single_platform_owner"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "session_version" not in columns:
        op.add_column(
            "users",
            sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"),
        )
    existing = {index["name"] for index in inspector.get_indexes("users")}
    if INDEX_NAME in existing:
        return
    op.create_index(
        INDEX_NAME,
        "users",
        ["role"],
        unique=True,
        postgresql_where=sa.text("role = 'platform_owner'"),
        sqlite_where=sa.text("role = 'platform_owner'"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        existing = {index["name"] for index in inspector.get_indexes("users")}
        if INDEX_NAME in existing:
            op.drop_index(INDEX_NAME, table_name="users")
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "session_version" in columns:
            op.drop_column("users", "session_version")
