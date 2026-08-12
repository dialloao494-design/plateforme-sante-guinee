"""
Patient mutation ownership — clinic-scoped create / update / archive.

Centralizes the tenant checks that routers/patient.py and clinical workflows
must apply consistently. Platform roles may break glass; clinic admins may
only touch patients in their own clinic.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.roles import PLATFORM_SCOPE_ROLES, user_has_any_role
from core.tenant import is_platform_admin, user_clinic_id
from models.user import User


class PatientOwnershipPolicy:
    """Single source of truth for patient tenant mutation authorization."""

    @staticmethod
    def actor_clinic_id(db: Session, current_user: User) -> int | None:
        return user_clinic_id(current_user, db)

    @staticmethod
    def assert_can_mutate_patient(
        db: Session,
        current_user: User,
        patient: models.Patient,
    ) -> None:
        """Clinic admins may only mutate patients that belong to their clinic."""
        if is_platform_admin(current_user):
            return
        cid = PatientOwnershipPolicy.actor_clinic_id(db, current_user)
        if cid is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        # Fail closed: unscoped/legacy patients (clinic_id NULL) are not
        # mutable by clinic-scoped administrators.
        if patient.clinic_id is None or patient.clinic_id != cid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

    @staticmethod
    def resolve_create_clinic_id(db: Session, current_user: User) -> int | None:
        """
        Clinic id assigned on patient creation.

        Platform admins may create unscoped patients (clinic_id=None).
        Clinic admins must have a clinic assignment.
        """
        if is_platform_admin(current_user):
            return PatientOwnershipPolicy.actor_clinic_id(db, current_user)
        cid = PatientOwnershipPolicy.actor_clinic_id(db, current_user)
        if cid is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        return cid

    @staticmethod
    def assert_linked_user_for_clinic(
        db: Session,
        *,
        user_id: int,
        clinic_id: int | None,
        current_user: User,
    ) -> User:
        """
        Ensure a supplied account link is safe for the creating/updating admin.

        - Target user must exist and be active.
        - Target must have role ``patient`` (clinical records must not bind staff).
        - For clinic-scoped actors, target.clinic_id must match the actor clinic
          (or be unset only when platform creates).
        """
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found",
            )
        if not getattr(target, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user is inactive",
            )
        if (target.role or "").strip().lower() != "patient":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Patient records may only link to patient-role accounts",
            )

        if is_platform_admin(current_user):
            return target

        if clinic_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        if target.clinic_id is None or target.clinic_id != clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Linked user belongs to another clinic",
            )
        return target

    @staticmethod
    def assert_can_relink_user(
        db: Session,
        *,
        current_user: User,
        patient: models.Patient,
        new_user_id: int,
    ) -> User:
        """Relinking to a different account is platform-only, with validation."""
        if not user_has_any_role(current_user.role, PLATFORM_SCOPE_ROLES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Relinking patient to a different user requires platform privileges",
            )
        return PatientOwnershipPolicy.assert_linked_user_for_clinic(
            db,
            user_id=new_user_id,
            clinic_id=patient.clinic_id,
            current_user=current_user,
        )
