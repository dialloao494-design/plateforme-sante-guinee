"""Clinic-scoped patient resolution for portal and CIS flows."""

from __future__ import annotations

from sqlalchemy.orm import Session

import models
from models.user import User


def get_or_create_clinic_patient(
    db: Session,
    *,
    user: User,
    clinic_id: int,
    defaults: dict | None = None,
) -> models.Patient:
    """One patient row per (clinic_id, user_id) for portal accounts."""
    existing = (
        db.query(models.Patient)
        .filter(
            models.Patient.user_id == user.id,
            models.Patient.clinic_id == clinic_id,
        )
        .first()
    )
    if existing:
        return existing

    shell = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    data = defaults or {}
    patient = models.Patient(
        clinic_id=clinic_id,
        user_id=user.id,
        first_name=data.get("first_name") or (shell.first_name if shell else "Patient"),
        last_name=data.get("last_name") or (shell.last_name if shell else f"User{user.id}"),
        age=data.get("age", shell.age if shell else 0),
        gender=data.get("gender") or (shell.gender if shell else "unknown"),
        phone=data.get("phone") or (shell.phone if shell else None),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    from services.medical_history_service import ensure_medical_record

    ensure_medical_record(db, patient.id)
    return patient
