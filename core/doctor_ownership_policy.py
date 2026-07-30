"""
Doctor resource ownership policy — RBAC for clinician-scoped mutations.

Doctors may only mutate resources bound to their own ``doctors.id`` profile.
Administrators retain cross-tenant oversight (by design, audited at router layer).
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.tenant import is_platform_admin, user_clinic_id
from models.user import User


class DoctorOwnershipPolicy:
    """Single source of truth for doctor ↔ resource ownership checks."""

    @staticmethod
    def resolve_doctor_profile(db: Session, user_id: int) -> Optional[models.Doctor]:
        return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()

    @staticmethod
    def assert_can_mutate_doctor_resource(
        db: Session,
        *,
        target_doctor_id: int,
        current_user: User,
        resource: str = "doctor resource",
    ) -> models.Doctor | None:
        """
        Ensure the authenticated user may write to ``target_doctor_id``.

        Returns the caller's Doctor row when role is doctor (for downstream use).
        Raises 403 when a doctor targets another practitioner's data.
        Raises 404 when a doctor account has no profile.
        """
        doctor = db.query(models.Doctor).filter(models.Doctor.id == target_doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found",
            )

        if is_platform_admin(current_user):
            return None

        if current_user.role in ("clinic_admin", "admin"):
            actor_clinic_id = user_clinic_id(current_user, db)
            if actor_clinic_id != doctor.clinic_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Doctor belongs to another clinic",
                )
            return None

        if current_user.role != "doctor":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to modify {resource}",
            )

        own_doctor = DoctorOwnershipPolicy.resolve_doctor_profile(db, current_user.id)
        if not own_doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor profile not found",
            )

        if own_doctor.id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify another doctor's schedule",
            )

        return own_doctor

    @staticmethod
    def assert_availability_slot_belongs_to_doctor(
        slot: models.DoctorAvailability | None,
        *,
        doctor_id: int,
    ) -> models.DoctorAvailability:
        if not slot or slot.doctor_id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Availability slot not found",
            )
        return slot
