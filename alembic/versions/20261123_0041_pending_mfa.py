"""Stage MFA enrollment separately from the active factor."""

from alembic import op
import sqlalchemy as sa

revision = "20261123_0041_pending_mfa"
down_revision = "20260909_0040_authentication_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("users"):
        return
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "mfa_pending_secret" not in columns:
        op.add_column("users", sa.Column("mfa_pending_secret", sa.String(), nullable=True))
    if "mfa_pending_expires_at" not in columns:
        op.add_column("users", sa.Column("mfa_pending_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("users"):
        return
    with op.batch_alter_table("users") as batch:
        batch.drop_column("mfa_pending_expires_at")
        batch.drop_column("mfa_pending_secret")
