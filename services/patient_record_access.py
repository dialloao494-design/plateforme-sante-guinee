"""
RBAC for server-side patient dossier access — clinic-scoped multi-tenant.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.clinical_access import user_clinic_id
from core.roles import CLINICAL_STAFF_ROLES, CLINIC_ADMIN_ROLES
from core.tenant import is_clinic_admin, is_platform_admin
from models.user import User


def _get_patient_or_404(db: Session, patient_id: int) -> models.Patient:
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


def _get_patient_for_user(db: Session, user_id: int) -> models.Patient | None:
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def _get_doctor_for_user(db: Session, user_id: int) -> models.Doctor | None:
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def resolve_dossier_clinic_id(db: Session, current_user: User, patient: models.Patient) -> int:
    """
    Clinic scope for dossier reads/writes.
    Staff use home clinic; doctors use their clinic; patients use patient.clinic_id.
    """
    if current_user.role == "patient":
        if patient.clinic_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient profile has no clinic assignment",
            )
        return patient.clinic_id

    if current_user.role == "doctor":
        doctor = _get_doctor_for_user(db, current_user.id)
        if not doctor or not doctor.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor is not assigned to a clinic",
            )
        return doctor.clinic_id

    cid = user_clinic_id(current_user)
    if cid is None:
        if is_platform_admin(current_user) and patient.clinic_id:
            return patient.clinic_id
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to a clinic",
        )
    return cid


class PatientRecordAccessPolicy:
    @staticmethod
    def assert_can_read_dossier(db: Session, current_user: User, patient_id: int) -> models.Patient:
        patient = _get_patient_or_404(db, patient_id)

        if is_platform_admin(current_user):
            return patient

        if current_user.role == "patient":
            own = _get_patient_for_user(db, current_user.id)
            if not own or own.id != patient.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return patient

        clinic_id = resolve_dossier_clinic_id(db, current_user, patient)
        if patient.clinic_id is None or patient.clinic_id != clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this patient dossier",
            )
        return patient

    @staticmethod
    def dossier_clinic_id(db: Session, current_user: User, patient: models.Patient) -> int:
        """Clinic filter for timeline/history queries after access is granted."""
        PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient.id)
        if is_platform_admin(current_user):
            if patient.clinic_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Patient has no clinic_id",
                )
            return patient.clinic_id
        return resolve_dossier_clinic_id(db, current_user, patient)

    @staticmethod
    def assert_can_write_clinical(
        db: Session, current_user: User, patient_id: int
    ) -> tuple[models.Patient, models.Doctor | None]:
        patient = PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)

        if is_platform_admin(current_user) or current_user.role in CLINIC_ADMIN_ROLES:
            return patient, None

        if current_user.role == "doctor":
            doctor = _get_doctor_for_user(db, current_user.id)
            if not doctor:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Doctor profile not found",
                )
            return patient, doctor

        if current_user.role in CLINICAL_STAFF_ROLES:
            return patient, None

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff can modify clinical records",
        )

    @staticmethod
    def resolve_doctor_id(db: Session, current_user: User, doctor: models.Doctor | None) -> int | None:
        if doctor is not None:
            return doctor.id
        if is_platform_admin(current_user) or is_clinic_admin(current_user):
            return None
        return None
