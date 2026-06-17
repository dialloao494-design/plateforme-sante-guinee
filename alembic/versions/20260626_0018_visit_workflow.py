"""Patient visit workflow queues."""

from alembic import op
import sqlalchemy as sa

revision = "20260626_0018_visit_workflow"
down_revision = "20260625_0017_nutrition_immunization_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_visit_workflows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("clinical_visit_id", sa.Integer(), sa.ForeignKey("clinical_visits.id"), nullable=True),
        sa.Column("workflow_type", sa.String(32), nullable=False),
        sa.Column("current_department", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_patient_visit_workflows_clinic_id", "patient_visit_workflows", ["clinic_id"])
    op.create_index("ix_patient_visit_workflows_patient_id", "patient_visit_workflows", ["patient_id"])
    op.create_index("ix_patient_visit_workflows_current_department", "patient_visit_workflows", ["current_department"])
    op.create_index("ix_patient_visit_workflows_status", "patient_visit_workflows", ["status"])

    op.create_table(
        "patient_visit_workflow_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.Integer(), sa.ForeignKey("patient_visit_workflows.id"), nullable=False),
        sa.Column("department", sa.String(32), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="waiting"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_patient_visit_workflow_steps_workflow_id", "patient_visit_workflow_steps", ["workflow_id"])
    op.create_index("ix_patient_visit_workflow_steps_department", "patient_visit_workflow_steps", ["department"])


def downgrade() -> None:
    op.drop_table("patient_visit_workflow_steps")
    op.drop_table("patient_visit_workflows")
