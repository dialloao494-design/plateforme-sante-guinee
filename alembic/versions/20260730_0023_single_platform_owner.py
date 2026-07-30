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
    # Commit session_version independently of the unique-index step so a later
    # index failure cannot roll back the column (production UndefinedColumn).
    if "session_version" not in columns:
        with op.get_context().autocommit_block():
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
        inspector = sa.inspect(bind)
        columns = {column["name"] for column in inspector.get_columns("users")}

    # Demote duplicate platform_owner rows before unique index (keep lowest id).
    # Racing /platform/setup history otherwise breaks production migrations → 502.
    if "is_active" in columns:
        demote_sql = """
            UPDATE users
            SET role = 'patient',
                is_active = false
            WHERE role = 'platform_owner'
              AND id NOT IN (
                SELECT id FROM (
                  SELECT MIN(id) AS id FROM users WHERE role = 'platform_owner'
                ) keeper
              )
            """
    else:
        demote_sql = """
            UPDATE users
            SET role = 'patient'
            WHERE role = 'platform_owner'
              AND id NOT IN (
                SELECT id FROM (
                  SELECT MIN(id) AS id FROM users WHERE role = 'platform_owner'
                ) keeper
              )
            """
    op.execute(sa.text(demote_sql))

    existing = {index["name"] for index in inspector.get_indexes("users")}
    if INDEX_NAME in existing:
        return
    try:
        op.create_index(
            INDEX_NAME,
            "users",
            ["role"],
            unique=True,
            postgresql_where=sa.text("role = 'platform_owner'"),
            sqlite_where=sa.text("role = 'platform_owner'"),
        )
    except Exception:
        # Column work above must survive; index can be applied by ensure_* later.
        pass


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
