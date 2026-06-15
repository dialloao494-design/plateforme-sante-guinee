"""Multi-tenant isolation: patients.clinic_id, composite user uniqueness, admin role split."""

from alembic import op
import sqlalchemy as sa

revision = "20260623_0015_multi_tenant_patients"
down_revision = "20260622_0014_patient_user_id_unique"
branch_labels = None
depends_on = None


def _backfill_patient_clinic_id(bind) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE patients SET clinic_id = (
                SELECT rv.clinic_id FROM rendezvous rv
                WHERE rv.patient_id = patients.id AND rv.clinic_id IS NOT NULL
                ORDER BY rv.created_at DESC LIMIT 1
            )
            WHERE clinic_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE patients SET clinic_id = (
                SELECT a.clinic_id FROM admissions a
                WHERE a.patient_id = patients.id
                ORDER BY a.created_at DESC LIMIT 1
            )
            WHERE clinic_id IS NULL
            """
        )
    )


def _backfill_rendezvous_clinic_id(bind) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE rendezvous SET clinic_id = (
                SELECT d.clinic_id FROM doctors d WHERE d.id = rendezvous.doctor_id
            )
            WHERE clinic_id IS NULL
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("clinic_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_patients_clinic_id", "clinics", ["clinic_id"], ["id"])

    op.create_index("ix_patients_clinic_id", "patients", ["clinic_id"])
    _backfill_patient_clinic_id(bind)
    _backfill_rendezvous_clinic_id(bind)

    try:
        op.drop_index("uq_patients_user_id", table_name="patients")
    except Exception:
        pass

    if dialect == "sqlite":
        op.create_index(
            "uq_patients_clinic_user",
            "patients",
            ["clinic_id", "user_id"],
            unique=True,
        )
    else:
        op.create_unique_constraint(
            "uq_patients_clinic_user",
            "patients",
            ["clinic_id", "user_id"],
        )

    bind.execute(sa.text("UPDATE users SET role = 'clinic_admin' WHERE role = 'admin'"))


def downgrade() -> None:
    op.drop_index("uq_patients_clinic_user", table_name="patients")
    op.drop_index("ix_patients_clinic_id", table_name="patients")
    with op.batch_alter_table("patients") as batch:
        batch.drop_constraint("fk_patients_clinic_id", type_="foreignkey")
        batch.drop_column("clinic_id")
    try:
        op.create_index("uq_patients_user_id", "patients", ["user_id"], unique=True)
    except Exception:
        pass
