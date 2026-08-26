"""Extend nursing observations and continuity-of-care workflow.

Revision ID: 20260826_0036
Revises: 20260824_0035_ward_beds
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260826_0036"
down_revision = "20260824_0035_ward_beds"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "nurse_assessments" not in inspector.get_table_names():
        op.create_table(
            "nurse_assessments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), nullable=False),
            sa.Column("patient_id", sa.Integer(), nullable=False),
            sa.Column("admission_id", sa.Integer(), nullable=True),
            sa.Column("appointment_id", sa.Integer(), nullable=True),
            sa.Column("consultation_id", sa.Integer(), nullable=True),
            sa.Column("nurse_user_id", sa.Integer(), nullable=True),
            sa.Column("nurse_name", sa.String(length=128), nullable=True),
            sa.Column("temperature_c", sa.Float(), nullable=True),
            sa.Column("bp_systolic", sa.Integer(), nullable=True),
            sa.Column("bp_diastolic", sa.Integer(), nullable=True),
            sa.Column("heart_rate", sa.Integer(), nullable=True),
            sa.Column("respiratory_rate", sa.Integer(), nullable=True),
            sa.Column("height_cm", sa.Float(), nullable=True),
            sa.Column("weight_kg", sa.Float(), nullable=True),
            sa.Column("bmi", sa.Float(), nullable=True),
            sa.Column("vitals_observations", sa.Text(), nullable=True),
            sa.Column("reason_for_consultation", sa.Text(), nullable=True),
            sa.Column("history_of_present_illness", sa.Text(), nullable=True),
            sa.Column("medical_history", sa.Text(), nullable=True),
            sa.Column("surgical_history", sa.Text(), nullable=True),
            sa.Column("gynecological_history", sa.Text(), nullable=True),
            sa.Column("allergies", sa.Text(), nullable=True),
            sa.Column("current_treatments", sa.Text(), nullable=True),
            sa.Column("hospitalized_daily_vitals", sa.Text(), nullable=True),
            sa.Column("prescription", sa.Text(), nullable=True),
            sa.Column("nurse_notes", sa.Text(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_nurse_assessments_id", "nurse_assessments", ["id"])
        op.create_index("ix_nurse_assessments_clinic_id", "nurse_assessments", ["clinic_id"])
        op.create_index("ix_nurse_assessments_patient_id", "nurse_assessments", ["patient_id"])
        op.create_index("ix_nurse_assessments_admission_id", "nurse_assessments", ["admission_id"])
        op.create_index("ix_nurse_assessments_appointment_id", "nurse_assessments", ["appointment_id"])
        op.create_index("ix_nurse_assessments_consultation_id", "nurse_assessments", ["consultation_id"])
        inspector = inspect(bind)

    existing = {column["name"] for column in inspector.get_columns("nurse_assessments")}
    columns = (
        sa.Column("oxygen_saturation", sa.Integer(), nullable=True),
        sa.Column("pain_score", sa.Integer(), nullable=True),
        sa.Column("arm_circumference_cm", sa.Float(), nullable=True),
        sa.Column("head_circumference_cm", sa.Float(), nullable=True),
        sa.Column("consciousness_level", sa.String(length=32), nullable=True),
        sa.Column("escalation_level", sa.String(length=32), nullable=True),
        sa.Column("care_plan", sa.Text(), nullable=True),
        sa.Column("handover_sbar", sa.Text(), nullable=True),
        sa.Column("medication_administration", sa.Text(), nullable=True),
        sa.Column("specimen_collection", sa.Text(), nullable=True),
        sa.Column("wound_assessment", sa.Text(), nullable=True),
        sa.Column("safety_checklist", sa.Text(), nullable=True),
    )
    for column in columns:
        if column.name not in existing:
            op.add_column("nurse_assessments", column)


def downgrade():
    for name in (
        "safety_checklist", "wound_assessment", "specimen_collection",
        "medication_administration", "handover_sbar", "care_plan",
        "escalation_level", "consciousness_level", "head_circumference_cm",
        "arm_circumference_cm", "pain_score", "oxygen_saturation",
    ):
        op.drop_column("nurse_assessments", name)
