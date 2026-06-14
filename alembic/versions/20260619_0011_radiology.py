"""Radiology imaging orders and results."""

from alembic import op
import sqlalchemy as sa


revision = "20260619_0011_radiology"
down_revision = "20260618_0010_discharge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()
    insp = sa.inspect(bind)

    if not insp.has_table("imaging_orders"):
        op.create_table(
            "imaging_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("consultation_id", sa.Integer(), sa.ForeignKey("consultations.id"), nullable=False),
            sa.Column("modality", sa.String(32), nullable=False),
            sa.Column("body_part", sa.String(128), nullable=True),
            sa.Column("clinical_indication", sa.Text(), nullable=True),
            sa.Column("priority", sa.String(16), nullable=False, server_default="routine"),
            sa.Column("status", sa.String(32), nullable=False, server_default="ordered"),
            sa.Column("scheduled_at", datetime_type, nullable=True),
            sa.Column("ordered_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("imaging_results"):
        op.create_table(
            "imaging_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("imaging_orders.id"), nullable=False),
            sa.Column("findings", sa.Text(), nullable=True),
            sa.Column("impression", sa.Text(), nullable=True),
            sa.Column("recommendations", sa.Text(), nullable=True),
            sa.Column("attachment_url", sa.Text(), nullable=True),
            sa.Column("reported_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("validated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reported_at", datetime_type, nullable=True),
            sa.Column("validated_at", datetime_type, nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )


def downgrade() -> None:
    op.drop_table("imaging_results")
    op.drop_table("imaging_orders")
