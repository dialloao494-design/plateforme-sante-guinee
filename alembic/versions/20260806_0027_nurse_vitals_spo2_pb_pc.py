"""Add SpO2, PB (MUAC), PC (head circumference) to nurse assessments.

Revision ID: 20260806_0027_nurse_vitals_spo2_pb_pc
Revises: 20260802_0026_service_request_billing_integrity
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260806_0027_nurse_vitals_spo2_pb_pc"
down_revision = "20260802_0026_service_request_billing_integrity"
branch_labels = None
depends_on = None


def _table_columns(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    cols = _table_columns(bind, "nurse_assessments")
    if not cols:
        return
    if "spo2_percent" not in cols:
        op.add_column("nurse_assessments", sa.Column("spo2_percent", sa.Float(), nullable=True))
    if "muac_cm" not in cols:
        op.add_column("nurse_assessments", sa.Column("muac_cm", sa.Float(), nullable=True))
    if "head_circumference_cm" not in cols:
        op.add_column(
            "nurse_assessments",
            sa.Column("head_circumference_cm", sa.Float(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    cols = _table_columns(bind, "nurse_assessments")
    if not cols:
        return
    for name in ("head_circumference_cm", "muac_cm", "spo2_percent"):
        if name in cols:
            op.drop_column("nurse_assessments", name)
