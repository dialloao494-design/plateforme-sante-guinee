"""Preserve reported patient ages in days, weeks, months, or years.

Revision ID: 20260824_0031_patient_age_units
Revises: 20260819_0030_user_display_names
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260824_0031_patient_age_units"
down_revision = "20260819_0030_user_display_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "patients" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("patients")}
    if "age_value" not in columns:
        op.add_column("patients", sa.Column("age_value", sa.Integer(), nullable=True))
    if "age_unit" not in columns:
        op.add_column("patients", sa.Column("age_unit", sa.String(length=16), nullable=True))
    op.execute("UPDATE patients SET age_value = age WHERE age_value IS NULL")
    op.execute("UPDATE patients SET age_unit = 'years' WHERE age_unit IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    columns = {c["name"] for c in sa.inspect(bind).get_columns("patients")}
    if "age_unit" in columns:
        op.drop_column("patients", "age_unit")
    if "age_value" in columns:
        op.drop_column("patients", "age_value")
