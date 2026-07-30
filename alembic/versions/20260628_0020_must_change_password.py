"""Add must_change_password to users.

Idempotent for production DBs where the column already exists.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260628_0020_must_change_password"
down_revision = "20260627_0019_email_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "must_change_password" in cols:
        return
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "must_change_password" in cols:
        op.drop_column("users", "must_change_password")
