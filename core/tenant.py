"""Multi-tenant helpers — clinic ownership and cross-clinic guards."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from models.user import User


def user_clinic_id(user: User, db: Session | None = None) -> int | None:
    if user.clinic_id:
        return user.clinic_id
    if user.role == "doctor":
        profile = getattr(user, "doctor_profile", None)
        if profile is not None and profile.clinic_id:
            return profile.clinic_id
        if db is not None:
            doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
            if doc and doc.clinic_id:
                return doc.clinic_id
    if db is not None:
        staff = (
            db.query(models.ClinicStaff)
            .filter(models.ClinicStaff.user_id == user.id, models.ClinicStaff.is_active.is_(True))
            .order_by(models.ClinicStaff.id.desc())
            .first()
        )
        if staff:
            return staff.clinic_id
    return None


def is_platform_owner(user: User) -> bool:
    return user.role == "platform_owner"


def is_platform_admin(user: User) -> bool:
    """Cross-clinic support scope (legacy platform_admin or owner)."""
    return user.role in ("platform_owner", "platform_admin")


def is_clinic_admin(user: User) -> bool:
    return user.role in ("clinic_admin", "admin")


def is_any_admin(user: User) -> bool:
    return is_platform_admin(user) or is_clinic_admin(user)


def resolve_actor_clinic_id(user: User) -> int | None:
    """Clinic scope for staff; platform roles may have optional clinic_id."""
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
