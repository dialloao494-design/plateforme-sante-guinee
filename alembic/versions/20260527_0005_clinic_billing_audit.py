"""Clinic billing charges and audit log clinic_id."""

from alembic import op
import sqlalchemy as sa


revision = "20260527_0005_clinic_billing_audit"
down_revision = "20260526_0004_clinical_cis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()
    insp = sa.inspect(bind)

    if insp.has_table("clinical_audit_logs"):
        cols = {c["name"] for c in insp.get_columns("clinical_audit_logs")}
        if "clinic_id" not in cols:
            with op.batch_alter_table("clinical_audit_logs") as batch:
                batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        # patient_id may be NOT NULL from prior migration — relax for denied-access logs
        if dialect == "sqlite":
            pass  # create_all + inline migrations handle fresh SQLite
        elif dialect == "postgresql":
            op.alter_column("clinical_audit_logs", "patient_id", nullable=True)

    if not insp.has_table("clinic_charges"):
        op.create_table(
            "clinic_charges",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("charge_type", sa.String(32), nullable=False),
            sa.Column("source_type", sa.String(32), nullable=False),
            sa.Column("source_id", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("amount_gnf", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payment_status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("payment_method", sa.String(32), nullable=True),
            sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("paid_at", datetime_type, nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )
        op.create_index("ix_clinic_charges_clinic_id", "clinic_charges", ["clinic_id"])
        op.create_index("ix_clinic_charges_payment_status", "clinic_charges", ["payment_status"])
        op.create_index("ix_clinic_charges_created_at", "clinic_charges", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("clinic_charges"):
        op.drop_table("clinic_charges")
