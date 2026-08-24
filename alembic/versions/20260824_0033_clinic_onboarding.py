"""Persist clinic onboarding configuration and completion state.

Revision ID: 20260824_0033_clinic_onboarding
Revises: 20260824_0032_hospitalization_stay_fields
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260824_0033_clinic_onboarding"
down_revision = "20260824_0032_hospitalization_stay_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "clinics" not in sa.inspect(bind).get_table_names():
        return
    existing = {column["name"] for column in sa.inspect(bind).get_columns("clinics")}
    if "onboarding_config_json" not in existing:
        op.add_column("clinics", sa.Column("onboarding_config_json", sa.Text(), nullable=True))
    if "onboarding_completed_at" not in existing:
        op.add_column("clinics", sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if "clinics" not in sa.inspect(bind).get_table_names():
        return
    existing = {column["name"] for column in sa.inspect(bind).get_columns("clinics")}
    if "onboarding_completed_at" in existing:
        op.drop_column("clinics", "onboarding_completed_at")
    if "onboarding_config_json" in existing:
        op.drop_column("clinics", "onboarding_config_json")
