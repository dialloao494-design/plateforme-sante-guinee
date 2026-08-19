"""Store editable display names for user accounts.

Revision ID: 20260819_0030_user_display_names
Revises: 20260818_0029_patient_registration_dedupe
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260819_0030_user_display_names"
down_revision = "20260818_0029_patient_registration_dedupe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "first_name" not in columns:
        op.add_column("users", sa.Column("first_name", sa.String(length=128), nullable=True))
    if "last_name" not in columns:
        op.add_column("users", sa.Column("last_name", sa.String(length=128), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "last_name" in columns:
        op.drop_column("users", "last_name")
    if "first_name" in columns:
        op.drop_column("users", "first_name")
