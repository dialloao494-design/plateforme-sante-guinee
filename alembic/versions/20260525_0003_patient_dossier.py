"""Patient dossier MVP — clinical notes, summaries, documents, audit log."""

from alembic import op
import sqlalchemy as sa


revision = "20260525_0003_patient_dossier"
down_revision = "0002_doctor_geo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()

    with op.batch_alter_table("patients", schema=None) as batch_op:
        batch_op.add_column(sa.Column("date_of_birth", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("address", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("emergency_contact", sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column("created_at", datetime_type, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)
        )
        batch_op.add_column(
            sa.Column("updated_at", datetime_type, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)
        )

    op.create_table(
        "clinical_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("rendezvous.id"), nullable=True),
        sa.Column("note_type", sa.String(length=32), nullable=False, server_default="consultation"),
        sa.Column("contenu", sa.Text(), nullable=False),
        sa.Column("created_at", datetime_type, nullable=False),
        sa.Column("updated_at", datetime_type, nullable=False),
    )
    op.create_index("ix_clinical_notes_patient_id", "clinical_notes", ["patient_id"])
    op.create_index("ix_clinical_notes_created_at", "clinical_notes", ["created_at"])

    op.create_table(
        "consultation_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("rendezvous.id"), nullable=True),
        sa.Column("diagnostic", sa.Text(), nullable=True),
        sa.Column("traitement", sa.Text(), nullable=True),
        sa.Column("recommandations", sa.Text(), nullable=True),
        sa.Column("created_at", datetime_type, nullable=False),
    )
    op.create_index("ix_consultation_summaries_patient_id", "consultation_summaries", ["patient_id"])

    op.create_table(
        "patient_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type_document", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("created_at", datetime_type, nullable=False),
    )
    op.create_index("ix_patient_documents_patient_id", "patient_documents", ["patient_id"])

    op.create_table(
        "clinical_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("timestamp", datetime_type, nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_clinical_audit_logs_patient_id", "clinical_audit_logs", ["patient_id"])
    op.create_index("ix_clinical_audit_logs_timestamp", "clinical_audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("clinical_audit_logs")
    op.drop_table("patient_documents")
    op.drop_table("consultation_summaries")
    op.drop_table("clinical_notes")
    with op.batch_alter_table("patients", schema=None) as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("emergency_contact")
        batch_op.drop_column("address")
        batch_op.drop_column("phone")
        batch_op.drop_column("date_of_birth")
