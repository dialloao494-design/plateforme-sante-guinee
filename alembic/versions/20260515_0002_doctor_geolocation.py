"""Add doctor latitude/longitude columns if missing.

Revision ID: 0002_doctor_geo
Revises: 0001_baseline
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0002_doctor_geo"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = inspect(bind)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "doctors" not in inspect(bind).get_table_names():
        # The historical baseline is a stamp-only migration. Empty databases are
        # bootstrapped from the complete SQLAlchemy registry before upgrading.
        return
    if not _has_column("doctors", "latitude"):
        op.add_column("doctors", sa.Column("latitude", sa.Float(), nullable=True))
    if not _has_column("doctors", "longitude"):
        op.add_column("doctors", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    if _has_column("doctors", "longitude"):
        op.drop_column("doctors", "longitude")
    if _has_column("doctors", "latitude"):
        op.drop_column("doctors", "latitude")
