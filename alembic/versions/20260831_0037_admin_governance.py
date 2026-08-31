"""Admin governance, audit context, and clinic suspension metadata.

Revision ID: 20260831_0037
Revises: 20260826_0036
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260831_0037"
down_revision = "20260826_0036"
branch_labels = None
depends_on = None


def _add(table: str, column: sa.Column) -> None:
    inspector = inspect(op.get_bind())
    # Recovery/stamped databases used by older installations can legitimately
    # omit tables that were never enabled.  A governance migration must not
    # make those databases impossible to upgrade.
    if not inspector.has_table(table):
        return
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade():
    _add("users", sa.Column("created_at", sa.DateTime(), nullable=True))
    if inspect(op.get_bind()).has_table("users"):
        op.execute("UPDATE users SET created_at = COALESCE(last_login_at, password_changed_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL")

    _add("clinical_audit_logs", sa.Column("user_agent", sa.String(length=512), nullable=True))
    _add("clinical_audit_logs", sa.Column("reason", sa.String(length=500), nullable=True))
    _add("clinical_audit_logs", sa.Column("before_json", sa.Text(), nullable=True))
    _add("clinical_audit_logs", sa.Column("after_json", sa.Text(), nullable=True))

    _add("clinics", sa.Column("suspended_at", sa.DateTime(), nullable=True))
    _add("clinics", sa.Column("suspension_reason", sa.Text(), nullable=True))
    _add("clinics", sa.Column("archived_at", sa.DateTime(), nullable=True))
    _add("clinics", sa.Column("configuration_json", sa.Text(), nullable=True))


def downgrade():
    for name in ("configuration_json", "archived_at", "suspension_reason", "suspended_at"):
        op.drop_column("clinics", name)
    for name in ("after_json", "before_json", "reason", "user_agent"):
        op.drop_column("clinical_audit_logs", name)
    op.drop_column("users", "created_at")
