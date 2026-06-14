"""Medical history, vitals, allergies, chronic conditions, follow-ups."""

from alembic import op
import sqlalchemy as sa

revision = "20260615_0007_medical_history"
down_revision = "20260528_0006_cashier_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from database_migrations import ensure_medical_history_schema

    ensure_medical_history_schema(bind.engine)


def downgrade() -> None:
    pass
