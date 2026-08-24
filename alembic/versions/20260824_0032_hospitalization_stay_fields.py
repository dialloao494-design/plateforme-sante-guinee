"""Add hospitalization duration, accommodation, and admission placement fields.

Revision ID: 20260824_0032_hospitalization_stay_fields
Revises: 20260824_0031_patient_age_units
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260824_0032_hospitalization_stay_fields"
down_revision = "20260824_0031_patient_age_units"
branch_labels = None
depends_on = None


def _add_missing(table: str, columns: list[sa.Column]) -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_columns(table)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table, column)


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "clinic_service_requests" in tables:
        _add_missing("clinic_service_requests", [
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("duration_value", sa.Integer(), nullable=True),
            sa.Column("duration_unit", sa.String(length=16), nullable=True),
            sa.Column("specialty_code", sa.String(length=64), nullable=True),
            sa.Column("accommodation_type", sa.String(length=32), nullable=True),
        ])
    if "admissions" in tables:
        _add_missing("admissions", [
            sa.Column("bed_number", sa.String(length=32), nullable=True),
            sa.Column("cabin_number", sa.String(length=32), nullable=True),
        ])


def downgrade() -> None:
    bind = op.get_bind()
    for table, names in (
        ("admissions", ["cabin_number", "bed_number"]),
        ("clinic_service_requests", ["accommodation_type", "specialty_code", "duration_unit", "duration_value", "quantity"]),
    ):
        if table not in sa.inspect(bind).get_table_names():
            continue
        existing = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        for name in names:
            if name in existing:
                op.drop_column(table, name)
