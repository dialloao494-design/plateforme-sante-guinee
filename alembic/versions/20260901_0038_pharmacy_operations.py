"""Pharmacy replenishment and refund workflows.

Revision ID: 20260901_0038
Revises: 20260831_0037
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260901_0038"
down_revision = "20260831_0037"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    if not inspector.has_table("pharmacy_stock_orders"):
        op.create_table(
            "pharmacy_stock_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("inventory_item_id", sa.Integer(), sa.ForeignKey("pharmacy_inventory.id"), nullable=True),
            sa.Column("medication_name", sa.String(length=255), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("supplier", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="ordered"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("received_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("ordered_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("received_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_pharmacy_stock_orders_clinic_id", "pharmacy_stock_orders", ["clinic_id"])
        op.create_index("ix_pharmacy_stock_orders_inventory_item_id", "pharmacy_stock_orders", ["inventory_item_id"])
        op.create_index("ix_pharmacy_stock_orders_status", "pharmacy_stock_orders", ["status"])
    if not inspector.has_table("pharmacy_refunds"):
        op.create_table(
            "pharmacy_refunds",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("charge_id", sa.Integer(), sa.ForeignKey("clinic_charges.id"), nullable=False),
            sa.Column("pharmacy_order_id", sa.Integer(), sa.ForeignKey("pharmacy_orders.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("refund_number", sa.String(length=32), nullable=False, unique=True),
            sa.Column("amount_gnf", sa.Integer(), nullable=False),
            sa.Column("refund_method", sa.String(length=32), nullable=False),
            sa.Column("reason", sa.String(length=64), nullable=False),
            sa.Column("reason_notes", sa.Text(), nullable=False),
            sa.Column("recipient_name", sa.String(length=255), nullable=False),
            sa.Column("recipient_phone", sa.String(length=32), nullable=False),
            sa.Column("items_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="paid"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        for column in ("clinic_id", "charge_id", "pharmacy_order_id", "patient_id", "refund_number", "status"):
            op.create_index(f"ix_pharmacy_refunds_{column}", "pharmacy_refunds", [column], unique=column == "refund_number")


def downgrade():
    op.drop_table("pharmacy_refunds")
    op.drop_table("pharmacy_stock_orders")
