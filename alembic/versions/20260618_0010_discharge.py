"""Patient discharge summaries."""

from alembic import op
import sqlalchemy as sa


revision = "20260618_0010_discharge"
down_revision = "20260617_0009_unified_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()
    insp = sa.inspect(bind)

    if not insp.has_table("discharge_summaries"):
        op.create_table(
            "discharge_summaries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("visit_id", sa.Integer(), sa.ForeignKey("clinical_visits.id"), nullable=True),
            sa.Column("admission_id", sa.Integer(), sa.ForeignKey("admissions.id"), nullable=True),
            sa.Column("consultation_id", sa.Integer(), sa.ForeignKey("consultations.id"), nullable=True),
            sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True),
            sa.Column("discharge_type", sa.String(32), nullable=False, server_default="ambulatory"),
            sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("diagnoses", sa.Text(), nullable=True),
            sa.Column("procedures", sa.Text(), nullable=True),
            sa.Column("medications", sa.Text(), nullable=True),
            sa.Column("clinical_summary", sa.Text(), nullable=True),
            sa.Column("follow_up_instructions", sa.Text(), nullable=True),
            sa.Column("invoice_validated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("archived_to_emr", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("discharged_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("discharged_at", datetime_type, nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )


def downgrade() -> None:
    op.drop_table("discharge_summaries")
