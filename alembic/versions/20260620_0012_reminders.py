"""WhatsApp appointment reminders."""

from alembic import op
import sqlalchemy as sa


revision = "20260620_0012_reminders"
down_revision = "20260619_0011_radiology"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    datetime_type = sa.DateTime(timezone=True) if dialect == "postgresql" else sa.DateTime()
    insp = sa.inspect(bind)

    if not insp.has_table("appointment_reminders"):
        op.create_table(
            "appointment_reminders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("rendezvous.id"), nullable=False),
            sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
            sa.Column("channel", sa.String(32), nullable=False, server_default="whatsapp"),
            sa.Column("reminder_type", sa.String(16), nullable=False),
            sa.Column("scheduled_at", datetime_type, nullable=False),
            sa.Column("sent_at", datetime_type, nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("whatsapp_message_id", sa.String(128), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
        )

    if not insp.has_table("reminder_events"):
        op.create_table(
            "reminder_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("reminder_id", sa.Integer(), sa.ForeignKey("appointment_reminders.id"), nullable=False),
            sa.Column("event_type", sa.String(32), nullable=False),
            sa.Column("payload", sa.Text(), nullable=True),
            sa.Column("created_at", datetime_type, nullable=False),
        )


def downgrade() -> None:
    op.drop_table("reminder_events")
    op.drop_table("appointment_reminders")
