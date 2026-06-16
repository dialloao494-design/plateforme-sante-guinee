"""Pharmacy inventory table."""

from alembic import op
import sqlalchemy as sa

revision = "20260621_0013_pharmacy_inventory"
down_revision = "20260620_0012_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("pharmacy_inventory"):
        return

    op.create_table(
        "pharmacy_inventory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("sku", sa.String(64), nullable=False),
        sa.Column("medication_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_level", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("unit_price_gnf", sa.Integer(), nullable=False, server_default="25000"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pharmacy_inventory_clinic_id", "pharmacy_inventory", ["clinic_id"])
    op.create_index("ix_pharmacy_inventory_sku", "pharmacy_inventory", ["sku"])


def downgrade() -> None:
    op.drop_index("ix_pharmacy_inventory_sku", table_name="pharmacy_inventory")
    op.drop_index("ix_pharmacy_inventory_clinic_id", table_name="pharmacy_inventory")
    op.drop_table("pharmacy_inventory")
