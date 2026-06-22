"""Patient intake fields (AASMA reception) + doctor medicine deliveries."""

from alembic import op
import sqlalchemy as sa

revision = "20260628_0021_patient_intake_aasma"
down_revision = "20260628_0020_must_change_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("mother_name", sa.String(255), nullable=True))
    op.add_column("patients", sa.Column("profession", sa.String(128), nullable=True))
    op.add_column("patients", sa.Column("quartier", sa.String(255), nullable=True))
    op.add_column("patients", sa.Column("visit_destination", sa.String(255), nullable=True))

    op.create_table(
        "doctor_medicine_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("patient_name", sa.String(255), nullable=False),
        sa.Column("medicine_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("doctor_name", sa.String(255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="doctor_office"),
        sa.Column("delivered_at", sa.DateTime(), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_doctor_medicine_deliveries_clinic_id", "doctor_medicine_deliveries", ["clinic_id"])
    op.create_index("ix_doctor_medicine_deliveries_delivered_at", "doctor_medicine_deliveries", ["delivered_at"])


def downgrade() -> None:
    op.drop_table("doctor_medicine_deliveries")
    op.drop_column("patients", "visit_destination")
    op.drop_column("patients", "quartier")
    op.drop_column("patients", "profession")
    op.drop_column("patients", "mother_name")
