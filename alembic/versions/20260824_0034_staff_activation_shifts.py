"""Secure staff activation and clinic shift handoff.

Revision ID: 20260824_0034_staff_shifts
Revises: 20260824_0033_clinic_onboarding
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260824_0034_staff_shifts"
down_revision = "20260824_0033_clinic_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "staff_activation_tokens" not in tables:
        op.create_table(
            "staff_activation_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("delivery_status", sa.String(24), nullable=False, server_default="pending"),
            sa.Column("delivery_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_sent_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        for column in ("user_id", "created_by_user_id", "token_hash", "expires_at"):
            op.create_index(f"ix_staff_activation_tokens_{column}", "staff_activation_tokens", [column])
    if "clinic_operational_shifts" not in tables:
        op.create_table(
            "clinic_operational_shifts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="open"),
            sa.Column("opened_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("opened_at", sa.DateTime(), nullable=False),
            sa.Column("opening_snapshot_json", sa.Text(), nullable=False),
            sa.Column("opening_notes", sa.Text(), nullable=True),
            sa.Column("closed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("closing_snapshot_json", sa.Text(), nullable=True),
            sa.Column("closing_notes", sa.Text(), nullable=True),
            sa.Column("unresolved_acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        for column in ("clinic_id", "status", "opened_by_user_id", "closed_by_user_id"):
            op.create_index(f"ix_clinic_operational_shifts_{column}", "clinic_operational_shifts", [column])
        op.create_index(
            "uq_clinic_operational_shifts_one_open",
            "clinic_operational_shifts",
            ["clinic_id"],
            unique=True,
            postgresql_where=sa.text("status = 'open'"),
            sqlite_where=sa.text("status = 'open'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "clinic_operational_shifts" in tables:
        op.drop_table("clinic_operational_shifts")
    if "staff_activation_tokens" in tables:
        op.drop_table("staff_activation_tokens")
