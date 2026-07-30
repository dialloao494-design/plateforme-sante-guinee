"""Automatic outbox enqueue hooks for Clinic Node clinical writes."""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
_HOOKS_REGISTERED = False


def _clinic_node_enabled() -> bool:
    env = (os.getenv("ENVIRONMENT") or "").lower().strip()
    return env in {"clinic-node", "clinic_node"}


def _safe_enqueue(mapper, connection, target, entity_type: str, operation: str) -> None:
    if not _clinic_node_enabled():
        return
    try:
        clinic_id = getattr(target, "clinic_id", None)
        if clinic_id is None:
            return
        entity_uid = str(getattr(target, "id", None) or getattr(target, "uid", "") or "")
        payload: dict[str, Any] = {"id": getattr(target, "id", None), "clinic_id": clinic_id}
        # Minimal non-PHI-heavy identifiers for sync envelope; full row sync can expand later.
        for key in ("patient_id", "status", "updated_at", "created_at"):
            if hasattr(target, key):
                payload[key] = getattr(target, key)

        import uuid

        from services.clinic_node_sync_service import enqueue_outbox_event
        from sqlalchemy.orm import Session

        db = Session(bind=connection)
        try:
            enqueue_outbox_event(
                db,
                clinic_id=int(clinic_id),
                entity_type=entity_type,
                operation=operation,
                payload=payload,
                entity_uid=entity_uid or None,
                client_request_id=str(uuid.uuid4()),
                commit=True,
            )
        finally:
            db.close()
    except Exception as exc:
        logger.warning("sync hook enqueue failed for %s: %s", entity_type, exc)


def register_clinic_node_sync_hooks() -> None:
    global _HOOKS_REGISTERED
    if _HOOKS_REGISTERED:
        return
    if not _clinic_node_enabled():
        return

    try:
        import models  # noqa: F401
        from models.patient import Patient
    except Exception:
        Patient = None  # type: ignore

    targets: list[tuple[Any, str]] = []
    if Patient is not None:
        targets.append((Patient, "patient"))

    try:
        from models.clinical_consultation import ClinicalConsultation

        targets.append((ClinicalConsultation, "clinical_consultation"))
    except Exception:
        pass
    try:
        from models.lab_order import LabOrder

        targets.append((LabOrder, "lab_order"))
    except Exception:
        pass
    try:
        from models.pharmacy_order import PharmacyOrder

        targets.append((PharmacyOrder, "pharmacy_order"))
    except Exception:
        pass
    try:
        from models.clinic_charge import ClinicCharge

        targets.append((ClinicCharge, "clinic_charge"))
    except Exception:
        pass
    try:
        from models.pharmacy_inventory import PharmacyInventoryItem

        targets.append((PharmacyInventoryItem, "pharmacy_inventory"))
    except Exception:
        pass

    for model, entity_type in targets:

        def _make_insert(et: str):
            def _on_insert(mapper, connection, target):
                _safe_enqueue(mapper, connection, target, et, "create")

            return _on_insert

        def _make_update(et: str):
            def _on_update(mapper, connection, target):
                _safe_enqueue(mapper, connection, target, et, "update")

            return _on_update

        event.listen(model, "after_insert", _make_insert(entity_type))
        event.listen(model, "after_update", _make_update(entity_type))

    _HOOKS_REGISTERED = True
    logger.info("Clinic Node sync hooks registered for %s models", len(targets))
