"""Unified billing, clinical visits, invoices."""

from alembic import op
import sqlalchemy as sa


revision = "20260617_0009_unified_billing"
down_revision = "20260616_0008_hospitalization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()
    insp = sa.inspect(bind)

    if not insp.has_table("clinical_visits"):
        op.create_table(
            "clinical_visits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("rendezvous.id"), nullable=True),
            sa.Column("consultation_id", sa.Integer(), sa.ForeignKey("consultations.id"), nullable=True),
            sa.Column("admission_id", sa.Integer(), sa.ForeignKey("admissions.id"), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="open"),
            sa.Column("started_at", datetime_type, nullable=False),
            sa.Column("closed_at", datetime_type, nullable=True),
            sa.Column("discharged_at", datetime_type, nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("invoices"):
        op.create_table(
            "invoices",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("visit_id", sa.Integer(), sa.ForeignKey("clinical_visits.id"), nullable=True),
            sa.Column("invoice_number", sa.String(32), nullable=False, unique=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("total_amount_gnf", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("paid_amount_gnf", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("issued_at", datetime_type, nullable=True),
            sa.Column("paid_at", datetime_type, nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("invoice_items"):
        op.create_table(
            "invoice_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
            sa.Column("charge_type", sa.String(32), nullable=False),
            sa.Column("source_type", sa.String(32), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("unit_price_gnf", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("amount_gnf", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("clinic_charge_id", sa.Integer(), sa.ForeignKey("clinic_charges.id"), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
        )

    if not insp.has_table("payment_records"):
        op.create_table(
            "payment_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
            sa.Column("amount_gnf", sa.Integer(), nullable=False),
            sa.Column("payment_method", sa.String(32), nullable=False),
            sa.Column("reference", sa.String(128), nullable=True),
            sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("paid_at", datetime_type, nullable=False),
            sa.Column("created_at", datetime_type, nullable=False),
        )

    charge_cols = {c["name"] for c in insp.get_columns("clinic_charges")} if insp.has_table("clinic_charges") else set()
    if "visit_id" not in charge_cols:
        with op.batch_alter_table("clinic_charges") as batch:
            batch.add_column(sa.Column("visit_id", sa.Integer(), sa.ForeignKey("clinical_visits.id"), nullable=True))
            batch.add_column(sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("clinic_charges") as batch:
        batch.drop_column("invoice_id")
        batch.drop_column("visit_id")
    op.drop_table("payment_records")
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("clinical_visits")
