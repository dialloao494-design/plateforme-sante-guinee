"""Canonical patient dossier number (N° dossier) — shared by HIS and Alembic."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


def format_patient_number(clinic_id: int | None, patient_id: int) -> str:
    """PAT-{clinic:03d}-{id:06d} — matches ReceptionHIS registration."""
    clinic_key = 0 if clinic_id is None else int(clinic_id)
    return f"PAT-{clinic_key:03d}-{int(patient_id):06d}"


def _clinic_group_key(clinic_id: int | None) -> int:
    return 0 if clinic_id is None else int(clinic_id)


def backfill_patient_numbers(rows: Sequence[Mapping[str, Any]]) -> dict[int, str]:
    """
    Compute patient_number updates for legacy rows.

    1. Assign canonical numbers to rows with NULL patient_number.
    2. Resolve (clinic_id, patient_number) duplicates by reassigning each row
       to its canonical PAT-{clinic}-{id} value.

    Returns {patient_id: new_patient_number} for rows that must change.
    """
    updates: dict[int, str] = {}
    normalized: list[tuple[int, int | None, str | None]] = []
    for row in rows:
        pid = int(row["id"])
        clinic_id = row.get("clinic_id")
        if clinic_id is not None:
            clinic_id = int(clinic_id)
        current = row.get("patient_number")
        normalized.append((pid, clinic_id, current))

    for pid, clinic_id, current in normalized:
        if current is None or not str(current).strip():
            updates[pid] = format_patient_number(clinic_id, pid)

    # Apply pending NULL backfills before duplicate detection.
    effective: dict[int, str] = {}
    for pid, clinic_id, current in normalized:
        effective[pid] = updates.get(pid) or (str(current).strip() if current else "")

    by_key: dict[tuple[int, str], list[int]] = defaultdict(list)
    for pid, clinic_id, _current in normalized:
        pn = effective[pid]
        if not pn:
            continue
        by_key[(_clinic_group_key(clinic_id), pn)].append(pid)

    for (_clinic_key, _pn), ids in by_key.items():
        if len(ids) <= 1:
            continue
        for pid in ids:
            clinic_id = next(c for i, c, _ in normalized if i == pid)
            updates[pid] = format_patient_number(clinic_id, pid)

    return updates
