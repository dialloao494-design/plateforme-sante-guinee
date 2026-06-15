"""Shared clinic context for tests (multi-tenant)."""

from __future__ import annotations

import models


def get_or_create_test_clinic(db_session, *, name: str = "Pytest Clinic") -> models.Clinic:
    clinic = db_session.query(models.Clinic).filter(models.Clinic.name == name).first()
    if clinic:
        return clinic
    clinic = models.Clinic(name=name, city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)
    return clinic


def bind_clinic_booking(
    db_session,
    *,
    doctor: models.Doctor,
    patient: models.Patient,
    clinic: models.Clinic | None = None,
) -> models.Clinic:
    clinic = clinic or get_or_create_test_clinic(db_session)
    if doctor.clinic_id is None:
        doctor.clinic_id = clinic.id
    if patient.clinic_id is None:
        patient.clinic_id = clinic.id
    db_session.commit()
    return clinic
