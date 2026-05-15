"""Baseline stamp for existing deployments (schema via SQLAlchemy models).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-15

Run `alembic upgrade head` after deploy. Fresh installs also use create_all in entrypoint.
"""

from typing import Sequence, Union

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
