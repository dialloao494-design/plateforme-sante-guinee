"""Allow multiple platform owners while keeping public setup one-time."""

from alembic import op
import sqlalchemy as sa

revision = "20260902_0039_multiple_platform_owners"
down_revision = "20260901_0038"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_users_single_platform_owner"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        indexes = {index["name"] for index in inspector.get_indexes("users")}
        if INDEX_NAME in indexes:
            op.drop_index(INDEX_NAME, table_name="users")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("users"):
        return
    indexes = {index["name"] for index in inspector.get_indexes("users")}
    if INDEX_NAME not in indexes:
        op.create_index(
            INDEX_NAME,
            "users",
            ["role"],
            unique=True,
            postgresql_where=sa.text("role = 'platform_owner'"),
            sqlite_where=sa.text("role = 'platform_owner'"),
        )
