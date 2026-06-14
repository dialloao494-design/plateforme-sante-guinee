"""Unique patients.user_id — one portal profile per user account."""

from alembic import op
import sqlalchemy as sa

revision = "20260622_0014_patient_user_id_unique"
down_revision = "20260621_0013_pharmacy_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    dupes = bind.execute(
        sa.text(
            """
            SELECT user_id, MIN(id) AS keep_id
            FROM patients
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    for row in dupes:
        bind.execute(
            sa.text(
                "UPDATE patients SET user_id = NULL "
                "WHERE user_id = :uid AND id != :keep_id"
            ),
            {"uid": row.user_id, "keep_id": row.keep_id},
        )

    if dialect == "sqlite":
        op.create_index("uq_patients_user_id", "patients", ["user_id"], unique=True)
    else:
        op.execute(
            "CREATE UNIQUE INDEX uq_patients_user_id ON patients (user_id) "
            "WHERE user_id IS NOT NULL"
        )

    op.create_index(
        "ix_clinical_audit_logs_clinic_patient",
        "clinical_audit_logs",
        ["clinic_id", "resource_type", "patient_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_clinical_audit_logs_clinic_patient", table_name="clinical_audit_logs")
    op.drop_index("uq_patients_user_id", table_name="patients")
