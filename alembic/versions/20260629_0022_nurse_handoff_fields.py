"""Birth date precision and nurse handoff fields."""

from alembic import op
import sqlalchemy as sa

revision = "20260629_0022_nurse_handoff_fields"
down_revision = "20260628_0021_patient_intake_aasma"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    return {col["name"] for col in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("patients") and "date_of_birth_precision" not in _columns("patients"):
        op.add_column(
            "patients",
            sa.Column("date_of_birth_precision", sa.String(16), nullable=False, server_default="full"),
        )

    if insp.has_table("nurse_assessments"):
        nurse_cols = _columns("nurse_assessments")
        if "hospitalized_daily_vitals" not in nurse_cols:
            op.add_column("nurse_assessments", sa.Column("hospitalized_daily_vitals", sa.Text(), nullable=True))
        if "prescription" not in nurse_cols:
            op.add_column("nurse_assessments", sa.Column("prescription", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("nurse_assessments"):
        nurse_cols = _columns("nurse_assessments")
        if "prescription" in nurse_cols:
            op.drop_column("nurse_assessments", "prescription")
        if "hospitalized_daily_vitals" in nurse_cols:
            op.drop_column("nurse_assessments", "hospitalized_daily_vitals")

    if insp.has_table("patients") and "date_of_birth_precision" in _columns("patients"):
        op.drop_column("patients", "date_of_birth_precision")
