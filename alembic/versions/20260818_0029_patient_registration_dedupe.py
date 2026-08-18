"""Prevent exact concurrent patient registrations while allowing confirmed duplicates.

Revision ID: 20260818_0029_patient_registration_dedupe
Revises: 20260812_0028_patient_number_integrity
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260818_0029_patient_registration_dedupe"
down_revision = "20260812_0028_patient_number_integrity"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_patients_clinic_registration_dedupe"


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "patients" not in insp.get_table_names():
        return
    columns = {column["name"] for column in insp.get_columns("patients")}
    if "registration_dedupe_key" not in columns:
        op.add_column(
            "patients",
            sa.Column("registration_dedupe_key", sa.String(length=64), nullable=True),
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("patients")}
    if INDEX_NAME not in indexes:
        if bind.dialect.name == "postgresql":
            op.create_index(
                INDEX_NAME,
                "patients",
                ["clinic_id", "registration_dedupe_key"],
                unique=True,
                postgresql_where=sa.text("registration_dedupe_key IS NOT NULL"),
            )
        else:
            op.create_index(
                INDEX_NAME,
                "patients",
                ["clinic_id", "registration_dedupe_key"],
                unique=True,
                sqlite_where=sa.text("registration_dedupe_key IS NOT NULL"),
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "patients" not in insp.get_table_names():
        return
    indexes = {index["name"] for index in insp.get_indexes("patients")}
    if INDEX_NAME in indexes:
        op.drop_index(INDEX_NAME, table_name="patients")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("patients")}
    if "registration_dedupe_key" in columns:
        op.drop_column("patients", "registration_dedupe_key")
