"""Nutrition, immunization, password reset, nutritionist/midwife roles.

Idempotent for production recovery: Railway DBs may already have these tables
(from ensure_*/create_all) while alembic_version is still at 0016.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260625_0017_nutrition_immunization_auth"
down_revision = "20260624_0016_platform_owner"
branch_labels = None
depends_on = None

# Keep aligned with database_migrations.ensure_user_roles_check_constraint so
# existing production rows (nurse/pev_agent/etc.) do not break CHECK recreate.
_NEW_ROLES = (
    "'patient', 'doctor', 'platform_owner', 'platform_admin', 'clinic_admin', 'admin', "
    "'receptionist', 'cashier', 'lab_technician', 'pharmacist', 'nutritionist', 'midwife', "
    "'pev_agent', 'nurse'"
)


def _ensure_index(insp, table: str, name: str, columns: list[str], *, unique: bool = False) -> None:
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if name in existing:
        return
    op.create_index(name, table, columns, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    if "users" in tables:
        if dialect == "sqlite":
            # SQLite batch path — best-effort; ignore missing constraint.
            try:
                with op.batch_alter_table("users") as batch:
                    batch.drop_constraint("ck_users_role_allowed", type_="check")
            except Exception:
                pass
            try:
                with op.batch_alter_table("users") as batch:
                    batch.create_check_constraint(
                        "ck_users_role_allowed", f"role IN ({_NEW_ROLES})"
                    )
            except Exception:
                pass
        else:
            op.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role_allowed"))
            # Guard against concurrent/duplicate constraint names on recovery deploys.
            op.execute(
                sa.text(
                    f"""
                    DO $$
                    BEGIN
                        ALTER TABLE users
                        ADD CONSTRAINT ck_users_role_allowed
                        CHECK (role IN ({_NEW_ROLES}));
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END
                    $$
                    """
                )
            )

    if "nutrition_assessments" not in tables:
        op.create_table(
            "nutrition_assessments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column(
                "consultation_id",
                sa.Integer(),
                sa.ForeignKey("consultations.id"),
                nullable=True,
            ),
            sa.Column("age_months", sa.Integer(), nullable=True),
            sa.Column("weight_kg", sa.Float(), nullable=True),
            sa.Column("height_cm", sa.Float(), nullable=True),
            sa.Column("muac_cm", sa.Float(), nullable=True),
            sa.Column("nutritional_status", sa.String(32), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "recorded_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("recorded_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        insp = sa.inspect(bind)
    if "nutrition_assessments" in set(insp.get_table_names()):
        _ensure_index(insp, "nutrition_assessments", "ix_nutrition_assessments_clinic_id", ["clinic_id"])
        _ensure_index(insp, "nutrition_assessments", "ix_nutrition_assessments_patient_id", ["patient_id"])

    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "vaccine_schedule_items" not in tables:
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
        insp = sa.inspect(bind)
    if "vaccine_schedule_items" in set(insp.get_table_names()):
        _ensure_index(
            insp,
            "vaccine_schedule_items",
            "ix_vaccine_schedule_items_vaccine_code",
            ["vaccine_code"],
        )

    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "immunization_records" not in tables:
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
            sa.Column(
                "administered_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        insp = sa.inspect(bind)
    if "immunization_records" in set(insp.get_table_names()):
        _ensure_index(insp, "immunization_records", "ix_immunization_records_clinic_id", ["clinic_id"])
        _ensure_index(insp, "immunization_records", "ix_immunization_records_patient_id", ["patient_id"])
        _ensure_index(
            insp,
            "immunization_records",
            "ix_immunization_records_vaccine_code",
            ["vaccine_code"],
        )

    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    if "password_reset_tokens" not in tables:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(128), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        insp = sa.inspect(bind)
    if "password_reset_tokens" in set(insp.get_table_names()):
        _ensure_index(insp, "password_reset_tokens", "ix_password_reset_tokens_user_id", ["user_id"])
        _ensure_index(
            insp,
            "password_reset_tokens",
            "ix_password_reset_tokens_token_hash",
            ["token_hash"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())
    for table in (
        "password_reset_tokens",
        "immunization_records",
        "vaccine_schedule_items",
        "nutrition_assessments",
    ):
        if table in tables:
            op.drop_table(table)

    _OLD = (
        "'patient', 'doctor', 'platform_owner', 'platform_admin', 'clinic_admin', 'admin', "
        "'receptionist', 'cashier', 'lab_technician', 'pharmacist'"
    )
    if dialect == "sqlite":
        with op.batch_alter_table("users") as batch:
            try:
                batch.drop_constraint("ck_users_role_allowed", type_="check")
            except Exception:
                pass
            batch.create_check_constraint("ck_users_role_allowed", f"role IN ({_OLD})")
    else:
        op.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role_allowed"))
        op.execute(
            sa.text(
                f"ALTER TABLE users ADD CONSTRAINT ck_users_role_allowed CHECK (role IN ({_OLD}))"
            )
        )
