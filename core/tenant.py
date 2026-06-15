"""Multi-tenant helpers — clinic ownership and cross-clinic guards."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from models.user import User


def user_clinic_id(user: User) -> int | None:
    if user.clinic_id:
        return user.clinic_id
    if user.role == "doctor" and user.doctor_profile and user.doctor_profile.clinic_id:
        return user.doctor_profile.clinic_id
    return None


def is_platform_admin(user: User) -> bool:
    return user.role == "platform_admin"


def is_clinic_admin(user: User) -> bool:
    return user.role in ("clinic_admin", "admin")


def is_any_admin(user: User) -> bool:
    return is_platform_admin(user) or is_clinic_admin(user)


def resolve_actor_clinic_id(user: User) -> int | None:
    """Clinic scope for staff; platform admins may have optional clinic_id."""
    if is_platform_admin(user):
        return user.clinic_id
    return user_clinic_id(user)


def assert_patient_in_clinic(
    db: Session,
    *,
    patient_id: int,
    clinic_id: int,
) -> models.Patient:
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if patient.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient belongs to another clinic",
        )
    return patient


def assert_patient_owned_by_clinic(patient: models.Patient, clinic_id: int) -> None:
    if patient.clinic_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient is not registered at this clinic",
        )
    if patient.clinic_id != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient belongs to another clinic",
        )
