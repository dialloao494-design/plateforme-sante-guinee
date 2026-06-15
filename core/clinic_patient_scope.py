"""Resolve which patient records belong to a clinic (tenant isolation)."""

from __future__ import annotations

from sqlalchemy.orm import Query, Session

import models


def clinic_patient_ids_query(db: Session, clinic_id: int) -> Query:
    """Distinct patient IDs owned by a clinic."""
    return (
        db.query(models.Patient.id.label("patient_id"))
        .filter(
            models.Patient.clinic_id == clinic_id,
            models.Patient.is_archived.is_(False),
        )
        .distinct()
    )


def patient_belongs_to_clinic(db: Session, *, patient_id: int, clinic_id: int) -> bool:
    return (
        db.query(models.Patient.id)
        .filter(
            models.Patient.id == patient_id,
            models.Patient.clinic_id == clinic_id,
            models.Patient.is_archived.is_(False),
        )
        .first()
        is not None
    )
