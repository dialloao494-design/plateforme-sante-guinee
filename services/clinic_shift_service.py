"""Clinic operational shift opening, closing, and handoff evidence."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

import models
from services.clinic_operations_service import clinic_operations_summary


class ShiftConflict(ValueError):
    pass


def _snapshot(db: Session, clinic_id: int, *, offline_pending_count: int, printer_ready: bool) -> dict:
    operations = clinic_operations_summary(db, clinic_id=clinic_id)
    active_admissions = db.query(models.Admission).filter(
        models.Admission.clinic_id == clinic_id,
        models.Admission.status.in_(("pending", "admitted", "in_care", "transferred")),
    ).count()
    unresolved = []
    labels = (
        ("reception_waiting", "patient(s) en attente à la réception"),
        ("doctor_waiting", "patient(s) en attente du médecin"),
        ("doctor_in_consultation", "consultation(s) en cours"),
        ("lab_active_orders", "examen(s) de laboratoire actif(s)"),
        ("pharmacy_active_orders", "ordonnance(s) de pharmacie active(s)"),
        ("cashier_pending_charges", "facture(s) à encaisser"),
    )
    for key, label in labels:
        if int(operations.get(key) or 0) > 0:
            unresolved.append({"key": key, "count": int(operations[key]), "label": label})
    if active_admissions:
        unresolved.append({"key": "active_admissions", "count": active_admissions, "label": "admission(s) active(s)"})
    if offline_pending_count:
        unresolved.append({"key": "offline_pending", "count": offline_pending_count, "label": "opération(s) hors ligne à synchroniser"})
    if not printer_ready:
        unresolved.append({"key": "printer", "count": 1, "label": "imprimante non vérifiée"})
    return {
        "captured_at": datetime.utcnow().isoformat(),
        "operations": operations,
        "active_admissions": active_admissions,
        "offline_pending_count": offline_pending_count,
        "printer_ready": printer_ready,
        "unresolved": unresolved,
    }


def serialize_shift(row: models.ClinicOperationalShift | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row.id,
        "clinic_id": row.clinic_id,
        "status": row.status,
        "opened_by_user_id": row.opened_by_user_id,
        "opened_at": row.opened_at,
        "opening_snapshot": json.loads(row.opening_snapshot_json),
        "opening_notes": row.opening_notes,
        "closed_by_user_id": row.closed_by_user_id,
        "closed_at": row.closed_at,
        "closing_snapshot": json.loads(row.closing_snapshot_json) if row.closing_snapshot_json else None,
        "closing_notes": row.closing_notes,
        "unresolved_acknowledged": row.unresolved_acknowledged,
    }


def current_shift(db: Session, clinic_id: int):
    return db.query(models.ClinicOperationalShift).filter(
        models.ClinicOperationalShift.clinic_id == clinic_id,
        models.ClinicOperationalShift.status == "open",
    ).order_by(models.ClinicOperationalShift.opened_at.desc()).first()


def open_shift(db: Session, *, clinic_id: int, actor_id: int, printer_ready: bool, offline_ready: bool, offline_pending_count: int, notes: str | None):
    if current_shift(db, clinic_id):
        raise ShiftConflict("Un poste est déjà ouvert pour cette clinique.")
    if (not printer_ready or not offline_ready or offline_pending_count > 0) and not (notes or "").strip():
        raise ShiftConflict("Expliquez l'exception avant d'ouvrir un poste avec un contrôle incomplet.")
    snapshot = _snapshot(db, clinic_id, offline_pending_count=offline_pending_count, printer_ready=printer_ready)
    snapshot["offline_ready"] = offline_ready
    row = models.ClinicOperationalShift(
        clinic_id=clinic_id,
        opened_by_user_id=actor_id,
        opening_snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        opening_notes=(notes or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def close_shift(db: Session, *, clinic_id: int, actor_id: int, printer_ready: bool, offline_pending_count: int, acknowledge_unresolved: bool, notes: str | None):
    row = current_shift(db, clinic_id)
    if not row:
        raise ShiftConflict("Aucun poste ouvert à clôturer.")
    snapshot = _snapshot(db, clinic_id, offline_pending_count=offline_pending_count, printer_ready=printer_ready)
    if snapshot["unresolved"] and not acknowledge_unresolved:
        raise ShiftConflict("Confirmez la transmission des éléments non résolus avant la clôture.")
    if snapshot["unresolved"] and not (notes or "").strip():
        raise ShiftConflict("Ajoutez une note de relève pour les éléments non résolus.")
    row.status = "closed"
    row.closed_by_user_id = actor_id
    row.closed_at = datetime.utcnow()
    row.closing_snapshot_json = json.dumps(snapshot, ensure_ascii=False)
    row.closing_notes = (notes or "").strip() or None
    row.unresolved_acknowledged = acknowledge_unresolved
    db.commit()
    db.refresh(row)
    return row
