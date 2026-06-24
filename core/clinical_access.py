"""
RBAC helpers for clinic-scoped clinical workflows.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.rbac import (
    ADMIN_ROLES,
    BILLING_PAY_ROLES,
    BILLING_READ_ROLES,
    BILLING_REVENUE_ROLES,
    CASHIER_ROLES,
    CLINIC_ADMIN_ROLES,
    DOCTOR_ROLES,
    LAB_QUEUE_ROLES,
    LAB_ROLES,
    PHARMACY_QUEUE_ROLES,
    PHARMACY_ROLES,
    PLATFORM_ADMIN_ROLES,
    RECEPTION_ROLES,
)
from core.roles import requires_clinic_assignment, user_has_any_role
from core.tenant import is_platform_admin, user_clinic_id
from models.user import User

PATIENT_LOOKUP_ROLES = (
    "receptionist",
    "cashier",
    "doctor",
    "lab_technician",
    "pharmacist",
    "clinic_admin",
    "admin",
    "nutritionist",
    "midwife",
    "nurse",
    "platform_admin",
    "platform_owner",
)

PATIENT_INTAKE_ROLES = PATIENT_LOOKUP_ROLES

CLINIC_OPS_ROLES = (
    "platform_owner",
    "platform_admin",
    "clinic_admin",
    "admin",
    "receptionist",
    "cashier",
    "doctor",
    "lab_technician",
    "pharmacist",
    "nutritionist",
    "midwife",
)

__all__ = [
    "RECEPTION_ROLES",
    "CASHIER_ROLES",
    "DOCTOR_ROLES",
    "LAB_ROLES",
    "PHARMACY_ROLES",
    "LAB_QUEUE_ROLES",
    "PHARMACY_QUEUE_ROLES",
    "ADMIN_ROLES",
    "CLINIC_ADMIN_ROLES",
    "PLATFORM_ADMIN_ROLES",
    "CLINIC_OPS_ROLES",
    "BILLING_READ_ROLES",
    "BILLING_PAY_ROLES",
    "BILLING_REVENUE_ROLES",
    "user_clinic_id",
    "PATIENT_LOOKUP_ROLES",
    "PATIENT_INTAKE_ROLES",
    "assert_role",
    "assert_clinic_access",
    "resolve_clinic_for_user",
    "doctor_for_user",
]


def assert_role(user: User, allowed: tuple[str, ...]) -> None:
    if not user_has_any_role(user.role, allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed)}",
        )


def assert_clinic_access(user: User, clinic_id: int, db: Session | None = None) -> None:
    if is_platform_admin(user):
        return
    user_cid = user_clinic_id(user, db)
    if user_cid != clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied for this clinic",
        )


def resolve_clinic_for_user(db: Session, user: User) -> models.Clinic:
    cid = user_clinic_id(user, db)
    if cid is None and is_platform_admin(user):
        clinic = (
            db.query(models.Clinic)
            .filter(models.Clinic.is_active.is_(True))
            .order_by(models.Clinic.id.asc())
            .first()
        )
        if clinic:
            return clinic
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucune clinique active. Créez une clinique depuis l'administration.",
        )
    if cid is None:
        if requires_clinic_assignment(user.role):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not assigned to a clinic",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not assigned to a clinic",
        )
    clinic = db.query(models.Clinic).filter(models.Clinic.id == cid).first()
    if not clinic or not clinic.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return clinic


def doctor_for_user(db: Session, user: User) -> models.Doctor:
    if user.role != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor only")
    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile missing")
    return doc
