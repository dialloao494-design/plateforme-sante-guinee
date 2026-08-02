"""Service-request billing columns + DSR invoice idempotency index.

Formalizes catalog_code / charge_type / unit_price_gnf on clinic_service_requests
(previously only added by runtime ensure_* helpers) and adds a partial unique
index so one service request cannot be billed on multiple invoice lines.

Revision ID: 20260802_0026_service_request_billing_integrity
Revises: 20260730_0025_ensure_session_version
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260802_0026_service_request_billing_integrity"
down_revision = "20260730_0025_ensure_session_version"
branch_labels = None
depends_on = None


def _table_columns(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _has_index(bind, table: str, name: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(idx.get("name") == name for idx in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    cols = _table_columns(bind, "clinic_service_requests")
    if cols:
        if "catalog_code" not in cols:
            op.add_column(
                "clinic_service_requests",
                sa.Column("catalog_code", sa.String(length=64), nullable=True),
            )
            op.create_index(
                "ix_clinic_service_requests_catalog_code",
                "clinic_service_requests",
                ["catalog_code"],
                unique=False,
            )
        if "charge_type" not in cols:
            op.add_column(
                "clinic_service_requests",
                sa.Column("charge_type", sa.String(length=64), nullable=True),
            )
        if "unit_price_gnf" not in cols:
            op.add_column(
                "clinic_service_requests",
                sa.Column("unit_price_gnf", sa.Integer(), nullable=True),
            )

    # One billed invoice line per service request (source_id = DSR id).
    if (
        _table_columns(bind, "invoice_items")
        and not _has_index(bind, "invoice_items", "uq_invoice_items_service_request_source")
    ):
        op.create_index(
            "uq_invoice_items_service_request_source",
            "invoice_items",
            ["source_id"],
            unique=True,
            postgresql_where=sa.text("source_type = 'service_request'"),
            sqlite_where=sa.text("source_type = 'service_request'"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "invoice_items", "uq_invoice_items_service_request_source"):
        op.drop_index("uq_invoice_items_service_request_source", table_name="invoice_items")

    cols = _table_columns(bind, "clinic_service_requests")
    if not cols:
        return
    if "unit_price_gnf" in cols:
        op.drop_column("clinic_service_requests", "unit_price_gnf")
    if "charge_type" in cols:
        op.drop_column("clinic_service_requests", "charge_type")
    if "catalog_code" in cols:
        try:
            op.drop_index("ix_clinic_service_requests_catalog_code", table_name="clinic_service_requests")
        except Exception:
            pass
        op.drop_column("clinic_service_requests", "catalog_code")
