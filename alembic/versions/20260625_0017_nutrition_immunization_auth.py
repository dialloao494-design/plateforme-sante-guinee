"""Nutrition, immunization, password reset, nutritionist/midwife roles."""

from alembic import op
import sqlalchemy as sa

revision = "20260625_0017_nutrition_immunization_auth"
down_revision = "20260624_0016_platform_owner"
branch_labels = None
depends_on = None

_NEW_ROLES = (
    "'patient', 'doctor', 'platform_owner', 'platform_admin', 'clinic_admin', 'admin', "
    "'receptionist', 'cashier', 'lab_technician', 'pharmacist', 'nutritionist', 'midwife'"
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)

    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_users_role_allowed", type_="check")
            batch.create_check_constraint("ck_users_role_allowed", f"role IN ({_NEW_ROLES})")
    else:
        op.drop_constraint("ck_users_role_allowed", "users", type_="check")
        op.create_check_constraint("ck_users_role_allowed", "users", f"role IN ({_NEW_ROLES})")

    op.create_table(
        "nutrition_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("consultation_id", sa.Integer(), sa.ForeignKey("consultations.id"), nullable=True),
        sa.Column("age_months", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("height_cm", sa.Float(), nullable=True),
        sa.Column("muac_cm", sa.Float(), nullable=True),
        sa.Column("nutritional_status", sa.String(32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_nutrition_assessments_clinic_id", "nutrition_assessments", ["clinic_id"])
    op.create_index("ix_nutrition_assessments_patient_id", "nutrition_assessments", ["patient_id"])

    op.create_table(
        "vaccine_schedule_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vaccine_code", sa.String(32), nullable=False),
        sa.Column("vaccine_name", sa.String(128), nullable=False),
        sa.Column("dose_label", sa.String(64), nullable=False),
        sa.Column("age_months", sa.Integer(), nullable=False),
        sa.Column("grace_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_vaccine_schedule_items_vaccine_code", "vaccine_schedule_items", ["vaccine_code"])

    op.create_table(
        "immunization_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("vaccine_code", sa.String(32), nullable=False),
        sa.Column("vaccine_name", sa.String(128), nullable=False),
        sa.Column("dose_label", sa.String(64), nullable=True),
        sa.Column("batch_number", sa.String(64), nullable=True),
        sa.Column("administered_at", sa.Date(), nullable=False),
        sa.Column("administered_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_immunization_records_clinic_id", "immunization_records", ["clinic_id"])
    op.create_index("ix_immunization_records_patient_id", "immunization_records", ["patient_id"])
    op.create_index("ix_immunization_records_vaccine_code", "immunization_records", ["vaccine_code"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("immunization_records")
    op.drop_table("vaccine_schedule_items")
    op.drop_table("nutrition_assessments")

    bind = op.get_bind()
    dialect = bind.dialect.name
    _OLD = (
        "'patient', 'doctor', 'platform_owner', 'platform_admin', 'clinic_admin', 'admin', "
        "'receptionist', 'cashier', 'lab_technician', 'pharmacist'"
    )
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint("ck_users_role_allowed", type_="check")
            batch.create_check_constraint("ck_users_role_allowed", f"role IN ({_OLD})")
    else:
        op.drop_constraint("ck_users_role_allowed", "users", type_="check")
        op.create_check_constraint("ck_users_role_allowed", "users", f"role IN ({_OLD})")
