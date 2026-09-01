"""Pharmacy replenishment workflow.

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
    if inspect(op.get_bind()).has_table("pharmacy_stock_orders"):
        return
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


def downgrade():
    op.drop_table("pharmacy_stock_orders")
