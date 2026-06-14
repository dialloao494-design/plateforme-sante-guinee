"""Modular clinical information system — schema."""

from alembic import op
import sqlalchemy as sa


revision = "20260526_0004_clinical_cis"
down_revision = "20260525_0003_patient_dossier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()
    insp = sa.inspect(bind)

    if not insp.has_table("clinics"):
        op.create_table(
            "clinics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("city", sa.String(128), nullable=True),
            sa.Column("phone", sa.String(32), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("clinic_staff"):
        op.create_table(
            "clinic_staff",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", datetime_type, nullable=False),
        )

    user_cols = {c["name"] for c in insp.get_columns("users")} if insp.has_table("users") else set()
    if "clinic_id" not in user_cols:
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
            if dialect == "postgresql":
                batch.drop_constraint("ck_users_role_allowed", type_="check")
                batch.create_check_constraint(
                    "ck_users_role_allowed",
                    "role IN ('patient', 'doctor', 'admin', 'receptionist', 'lab_technician', 'pharmacist')",
                )
            else:
                batch.drop_constraint("ck_users_role_allowed", type_="check")
                batch.create_check_constraint(
                    "ck_users_role_allowed",
                    "role IN ('patient', 'doctor', 'admin', 'receptionist', 'lab_technician', 'pharmacist')",
                )

    doctor_cols = {c["name"] for c in insp.get_columns("doctors")} if insp.has_table("doctors") else set()
    if "clinic_id" not in doctor_cols:
        with op.batch_alter_table("doctors") as batch:
            batch.add_column(sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=True))

    rdv_cols = {c["name"] for c in insp.get_columns("rendezvous")} if insp.has_table("rendezvous") else set()
    if "clinic_id" not in rdv_cols or "clinical_status" not in rdv_cols:
        with op.batch_alter_table("rendezvous") as batch:
            if "clinic_id" not in rdv_cols:
                batch.add_column(sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=True))
            if "clinical_status" not in rdv_cols:
                batch.add_column(
                    sa.Column("clinical_status", sa.String(32), nullable=False, server_default="scheduled")
                )

    if not insp.has_table("consultations"):
        op.create_table(
            "consultations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("rendezvous.id"), nullable=False, unique=True),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
            sa.Column("chief_complaint", sa.Text(), nullable=True),
            sa.Column("history", sa.Text(), nullable=True),
            sa.Column("examination", sa.Text(), nullable=True),
            sa.Column("diagnosis", sa.Text(), nullable=True),
            sa.Column("treatment_plan", sa.Text(), nullable=True),
            sa.Column("started_at", datetime_type, nullable=True),
            sa.Column("completed_at", datetime_type, nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("lab_orders"):
        op.create_table(
            "lab_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("consultation_id", sa.Integer(), sa.ForeignKey("consultations.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("ordered_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
            sa.Column("test_code", sa.String(64), nullable=False),
            sa.Column("test_name", sa.String(255), nullable=False),
            sa.Column("priority", sa.String(16), nullable=False, server_default="routine"),
            sa.Column("status", sa.String(32), nullable=False, server_default="ordered"),
            sa.Column("clinical_notes", sa.Text(), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("lab_results"):
        op.create_table(
            "lab_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("lab_order_id", sa.Integer(), sa.ForeignKey("lab_orders.id"), nullable=False, unique=True),
            sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("result_summary", sa.Text(), nullable=False),
            sa.Column("result_data", sa.Text(), nullable=True),
            sa.Column("reference_range", sa.String(255), nullable=True),
            sa.Column("interpretation", sa.Text(), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
            sa.Column("validated_at", datetime_type, nullable=True),
            sa.Column("validated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("prescriptions"):
        op.create_table(
            "prescriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("consultation_id", sa.Integer(), sa.ForeignKey("consultations.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("prescriber_doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )

    if not insp.has_table("prescription_items"):
        op.create_table(
            "prescription_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("prescription_id", sa.Integer(), sa.ForeignKey("prescriptions.id"), nullable=False),
            sa.Column("medication_name", sa.String(255), nullable=False),
            sa.Column("dosage", sa.String(128), nullable=False),
            sa.Column("route", sa.String(64), nullable=False, server_default="oral"),
            sa.Column("frequency", sa.String(128), nullable=False),
            sa.Column("duration_days", sa.Integer(), nullable=True),
            sa.Column("quantity", sa.Integer(), nullable=True),
            sa.Column("instructions", sa.Text(), nullable=True),
        )

    if not insp.has_table("pharmacy_orders"):
        op.create_table(
            "pharmacy_orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("prescription_id", sa.Integer(), sa.ForeignKey("prescriptions.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("prepared_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("dispensed_at", datetime_type, nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
            sa.Column("updated_at", datetime_type, nullable=False),
        )


def downgrade() -> None:
    op.drop_table("pharmacy_orders")
    op.drop_table("prescription_items")
    op.drop_table("prescriptions")
    op.drop_table("lab_results")
    op.drop_table("lab_orders")
    op.drop_table("consultations")
    with op.batch_alter_table("rendezvous") as batch:
        batch.drop_column("clinical_status")
        batch.drop_column("clinic_id")
    with op.batch_alter_table("doctors") as batch:
        batch.drop_column("clinic_id")
    with op.batch_alter_table("patients") as batch:
        batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
    with op.batch_alter_table("users") as batch:
        batch.drop_column("clinic_id")
    op.drop_table("clinic_staff")
    op.drop_table("clinics")
