"""API client request idempotency keys for offline/network replay safety.

Revision ID: 20260806_0027_api_client_idempotency
Revises: 20260802_0026_service_request_billing_integrity
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260806_0027_api_client_idempotency"
down_revision = "20260802_0026_service_request_billing_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "api_client_idempotency_keys" in insp.get_table_names():
        return
    op.create_table(
        "api_client_idempotency_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_request_id", sa.String(length=128), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("clinic_id", sa.Integer(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("client_request_id", name="uq_api_client_idempotency_request_id"),
    )
    op.create_index(
        "ix_api_client_idempotency_keys_client_request_id",
        "api_client_idempotency_keys",
        ["client_request_id"],
    )
    op.create_index(
        "ix_api_client_idempotency_keys_user_id",
        "api_client_idempotency_keys",
        ["user_id"],
    )
    op.create_index(
        "ix_api_client_idempotency_keys_clinic_id",
        "api_client_idempotency_keys",
        ["clinic_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "api_client_idempotency_keys" not in insp.get_table_names():
        return
    op.drop_index("ix_api_client_idempotency_keys_clinic_id", table_name="api_client_idempotency_keys")
    op.drop_index("ix_api_client_idempotency_keys_user_id", table_name="api_client_idempotency_keys")
    op.drop_index(
        "ix_api_client_idempotency_keys_client_request_id",
        table_name="api_client_idempotency_keys",
    )
    op.drop_table("api_client_idempotency_keys")
