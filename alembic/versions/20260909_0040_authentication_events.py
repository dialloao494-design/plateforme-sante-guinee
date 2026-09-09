"""Add privacy-conscious authentication event history."""

from alembic import op
import sqlalchemy as sa

revision = "20260909_0040_authentication_events"
down_revision = "20260902_0039_multiple_platform_owners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("authentication_events"):
        return
    op.create_table(
        "authentication_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("clinic_id", sa.Integer(), sa.ForeignKey("clinics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False, server_default="login"),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("email_fingerprint", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_authentication_events_user_id", "authentication_events", ["user_id"])
    op.create_index("ix_authentication_events_clinic_id", "authentication_events", ["clinic_id"])
    op.create_index("ix_authentication_events_succeeded", "authentication_events", ["succeeded"])
    op.create_index("ix_authentication_events_email_fingerprint", "authentication_events", ["email_fingerprint"])
    op.create_index("ix_authentication_events_occurred_at", "authentication_events", ["occurred_at"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("authentication_events"):
        op.drop_table("authentication_events")
