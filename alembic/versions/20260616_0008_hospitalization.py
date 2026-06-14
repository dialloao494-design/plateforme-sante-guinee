"""Admission and hospitalization schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260616_0008_hospitalization"
down_revision = "20260615_0007_medical_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()
    insp = sa.inspect(bind)

    if not insp.has_table("hospital_rooms"):
        op.create_table(
            "hospital_rooms",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("ward_name", sa.String(128), nullable=False),
            sa.Column("room_number", sa.String(32), nullable=False),
            sa.Column("room_type", sa.String(64), nullable=False, server_default="general"),
            sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )
        op.create_index("ix_hospital_rooms_clinic_id", "hospital_rooms", ["clinic_id"])
        op.create_index("ix_hospital_rooms_ward_name", "hospital_rooms", ["ward_name"])

    if not insp.has_table("hospital_beds"):
        op.create_table(
            "hospital_beds",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("room_id", sa.Integer(), sa.ForeignKey("hospital_rooms.id"), nullable=False),
            sa.Column("bed_number", sa.String(32), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="available"),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )
        op.create_index("ix_hospital_beds_room_id", "hospital_beds", ["room_id"])
        op.create_index("ix_hospital_beds_status", "hospital_beds", ["status"])

    if not insp.has_table("admissions"):
        op.create_table(
            "admissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("consultation_id", sa.Integer(), sa.ForeignKey("consultations.id"), nullable=True),
            sa.Column("admission_number", sa.String(32), nullable=False, unique=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("diagnosis_summary", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("admitted_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("admitted_at", datetime_type, nullable=True),
            sa.Column("discharged_at", datetime_type, nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )
        op.create_index("ix_admissions_clinic_id", "admissions", ["clinic_id"])
        op.create_index("ix_admissions_patient_id", "admissions", ["patient_id"])
        op.create_index("ix_admissions_status", "admissions", ["status"])

    if not insp.has_table("patient_stays"):
        op.create_table(
            "patient_stays",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("admission_id", sa.Integer(), sa.ForeignKey("admissions.id"), nullable=False),
            sa.Column("bed_id", sa.Integer(), sa.ForeignKey("hospital_beds.id"), nullable=False),
            sa.Column("assigned_at", datetime_type, nullable=False),
            sa.Column("released_at", datetime_type, nullable=True),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("transfer_reason", sa.Text(), nullable=True),
            sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
        )
        op.create_index("ix_patient_stays_admission_id", "patient_stays", ["admission_id"])
        op.create_index("ix_patient_stays_is_current", "patient_stays", ["is_current"])


def downgrade() -> None:
    op.drop_table("patient_stays")
    op.drop_table("admissions")
    op.drop_table("hospital_beds")
    op.drop_table("hospital_rooms")
