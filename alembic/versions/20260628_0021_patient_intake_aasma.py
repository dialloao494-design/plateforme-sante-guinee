"""Patient intake fields (AASMA reception) + doctor medicine deliveries.

Idempotent for production DBs where columns/tables already exist.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260628_0021_patient_intake_aasma"
down_revision = "20260628_0020_must_change_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "patients" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patients")}
        for name, col in (
            ("mother_name", sa.Column("mother_name", sa.String(255), nullable=True)),
            ("profession", sa.Column("profession", sa.String(128), nullable=True)),
            ("quartier", sa.Column("quartier", sa.String(255), nullable=True)),
            (
                "visit_destination",
                sa.Column("visit_destination", sa.String(255), nullable=True),
            ),
        ):
            if name not in cols:
                op.add_column("patients", col)

    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "doctor_medicine_deliveries" not in tables:
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
            sa.Column(
                "recorded_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        insp = sa.inspect(bind)

    if "doctor_medicine_deliveries" in set(insp.get_table_names()):
        existing = {idx["name"] for idx in insp.get_indexes("doctor_medicine_deliveries")}
        if "ix_doctor_medicine_deliveries_clinic_id" not in existing:
            op.create_index(
                "ix_doctor_medicine_deliveries_clinic_id",
                "doctor_medicine_deliveries",
                ["clinic_id"],
            )
        if "ix_doctor_medicine_deliveries_delivered_at" not in existing:
            op.create_index(
                "ix_doctor_medicine_deliveries_delivered_at",
                "doctor_medicine_deliveries",
                ["delivered_at"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "doctor_medicine_deliveries" in tables:
        op.drop_table("doctor_medicine_deliveries")
    if "patients" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patients")}
        for name in ("visit_destination", "quartier", "profession", "mother_name"):
            if name in cols:
                op.drop_column("patients", name)
