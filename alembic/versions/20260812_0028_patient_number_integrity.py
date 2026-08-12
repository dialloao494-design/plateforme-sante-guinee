"""Backfill patient_number and enforce per-clinic uniqueness.

Revision ID: 20260812_0028_patient_number_integrity
Revises: 20260806_0027_api_client_idempotency
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from core.patient_number import backfill_patient_numbers, format_patient_number

revision = "20260812_0028_patient_number_integrity"
down_revision = "20260806_0027_api_client_idempotency"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_patients_clinic_patient_number"


def _patients_columns(bind) -> set[str]:
    insp = sa.inspect(bind)
    if "patients" not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns("patients")}


def _apply_backfill(bind) -> None:
    cols = _patients_columns(bind)
    if "patient_number" not in cols:
        return
    rows = bind.execute(
        sa.text("SELECT id, clinic_id, patient_number FROM patients ORDER BY id")
    ).mappings().all()
    if not rows:
        return
    updates = backfill_patient_numbers(rows)
    for patient_id, patient_number in sorted(updates.items()):
        bind.execute(
            sa.text("UPDATE patients SET patient_number = :pn WHERE id = :id"),
            {"pn": patient_number, "id": patient_id},
        )


def _duplicate_groups(bind) -> list[tuple[int | None, str, int]]:
  """Return (clinic_id, patient_number, count) for conflicting groups."""
  dialect = bind.dialect.name
  if dialect == "postgresql":
    sql = sa.text(
        """
        SELECT clinic_id, patient_number, COUNT(*) AS cnt
        FROM patients
        WHERE patient_number IS NOT NULL
        GROUP BY clinic_id, patient_number
        HAVING COUNT(*) > 1
        """
    )
  else:
    sql = sa.text(
        """
        SELECT clinic_id, patient_number, COUNT(*) AS cnt
        FROM patients
        WHERE patient_number IS NOT NULL
        GROUP BY clinic_id, patient_number
        HAVING COUNT(*) > 1
        """
    )
  return [
    (row.clinic_id, row.patient_number, int(row.cnt))
    for row in bind.execute(sql).fetchall()
  ]


def _remaining_nulls(bind) -> int:
    return int(
        bind.execute(
            sa.text("SELECT COUNT(*) FROM patients WHERE patient_number IS NULL")
        ).scalar()
        or 0
    )


def upgrade() -> None:
    bind = op.get_bind()
    cols = _patients_columns(bind)
    if not cols:
        return

    if "patient_number" not in cols:
        op.add_column("patients", sa.Column("patient_number", sa.String(length=32), nullable=True))

    _apply_backfill(bind)

    # Last-resort: force canonical numbers for any stubborn duplicate groups.
    for _ in range(8):
        dupes = _duplicate_groups(bind)
        if not dupes:
            break
        for clinic_id, patient_number, _cnt in dupes:
            conflict_rows = bind.execute(
                sa.text(
                    """
                    SELECT id, clinic_id FROM patients
                    WHERE patient_number = :pn
                      AND (
                        (clinic_id IS NULL AND :cid IS NULL)
                        OR clinic_id = :cid
                      )
                    ORDER BY id
                    """
                ),
                {"pn": patient_number, "cid": clinic_id},
            ).fetchall()
            for row in conflict_rows:
                bind.execute(
                    sa.text("UPDATE patients SET patient_number = :pn WHERE id = :id"),
                    {
                        "pn": format_patient_number(row.clinic_id, row.id),
                        "id": row.id,
                    },
                )

    insp = sa.inspect(bind)
    indexes = {idx["name"] for idx in insp.get_indexes("patients")}
    if INDEX_NAME not in indexes and not _duplicate_groups(bind):
        dialect = bind.dialect.name
        if dialect == "postgresql":
            op.create_index(
                INDEX_NAME,
                "patients",
                ["clinic_id", "patient_number"],
                unique=True,
                postgresql_where=sa.text("patient_number IS NOT NULL"),
            )
        else:
            op.create_index(
                INDEX_NAME,
                "patients",
                ["clinic_id", "patient_number"],
                unique=True,
                sqlite_where=sa.text("patient_number IS NOT NULL"),
            )

    # NOT NULL only when every row has a dossier number and uniqueness holds.
    cols = _patients_columns(bind)
    if (
        "patient_number" in cols
        and _remaining_nulls(bind) == 0
        and not _duplicate_groups(bind)
    ):
        dialect = bind.dialect.name
        nullable = next(
            c["nullable"]
            for c in sa.inspect(bind).get_columns("patients")
            if c["name"] == "patient_number"
        )
        if nullable:
            if dialect == "postgresql":
                op.alter_column("patients", "patient_number", nullable=False)
            else:
                # SQLite cannot ALTER COLUMN; app + partial unique index enforce new rows.
                pass


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "patients" not in insp.get_table_names():
        return
    indexes = {idx["name"] for idx in insp.get_indexes("patients")}
    if INDEX_NAME in indexes:
        op.drop_index(INDEX_NAME, table_name="patients")
    # Keep backfilled values and nullable column (production safety).
