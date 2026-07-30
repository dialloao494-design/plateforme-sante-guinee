"""Patient visit workflow queues.

Idempotent: tables may already exist when alembic_version lags behind runtime schema.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260626_0018_visit_workflow"
down_revision = "20260625_0017_nutrition_immunization_auth"
branch_labels = None
depends_on = None


def _ensure_index(insp, table: str, name: str, columns: list[str]) -> None:
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if name in existing:
        return
    op.create_index(name, table, columns)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "patient_visit_workflows" not in tables:
        op.create_table(
            "patient_visit_workflows",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column(
                "clinical_visit_id",
                sa.Integer(),
                sa.ForeignKey("clinical_visits.id"),
                nullable=True,
            ),
            sa.Column("workflow_type", sa.String(32), nullable=False),
            sa.Column("current_department", sa.String(32), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        insp = sa.inspect(bind)
    if "patient_visit_workflows" in set(insp.get_table_names()):
        _ensure_index(insp, "patient_visit_workflows", "ix_patient_visit_workflows_clinic_id", ["clinic_id"])
        _ensure_index(insp, "patient_visit_workflows", "ix_patient_visit_workflows_patient_id", ["patient_id"])
        _ensure_index(
            insp,
            "patient_visit_workflows",
            "ix_patient_visit_workflows_current_department",
            ["current_department"],
        )
        _ensure_index(insp, "patient_visit_workflows", "ix_patient_visit_workflows_status", ["status"])

    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "patient_visit_workflow_steps" not in tables:
        op.create_table(
            "patient_visit_workflow_steps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "workflow_id",
                sa.Integer(),
                sa.ForeignKey("patient_visit_workflows.id"),
                nullable=False,
            ),
            sa.Column("department", sa.String(32), nullable=False),
            sa.Column("step_order", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="waiting"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column(
                "completed_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
        )
        insp = sa.inspect(bind)
    if "patient_visit_workflow_steps" in set(insp.get_table_names()):
        _ensure_index(
            insp,
            "patient_visit_workflow_steps",
            "ix_patient_visit_workflow_steps_workflow_id",
            ["workflow_id"],
        )
        _ensure_index(
            insp,
            "patient_visit_workflow_steps",
            "ix_patient_visit_workflow_steps_department",
            ["department"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "patient_visit_workflow_steps" in tables:
        op.drop_table("patient_visit_workflow_steps")
    if "patient_visit_workflows" in tables:
        op.drop_table("patient_visit_workflows")
