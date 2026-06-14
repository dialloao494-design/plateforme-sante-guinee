"""
RBAC for server-side patient dossier access.

- admin: all patients
- doctor: patients with at least one rendezvous link
- clinical staff (receptionist, lab_technician, pharmacist): patients with clinic appointment
- patient: own dossier only (user_id match)
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.clinical_access import user_clinic_id
from core.roles import CLINICAL_STAFF_ROLES
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


def _doctor_linked_to_patient(db: Session, doctor_id: int, patient_id: int) -> bool:
    return (
        db.query(models.RendezVous)
        .filter(
            models.RendezVous.doctor_id == doctor_id,
            models.RendezVous.patient_id == patient_id,
        )
        .first()
        is not None
    )


def _clinic_linked_to_patient(db: Session, clinic_id: int, patient_id: int) -> bool:
    return (
        db.query(models.RendezVous)
        .filter(
            models.RendezVous.clinic_id == clinic_id,
            models.RendezVous.patient_id == patient_id,
        )
        .first()
        is not None
    )


class PatientRecordAccessPolicy:
    @staticmethod
    def assert_can_read_dossier(db: Session, current_user: User, patient_id: int) -> models.Patient:
        patient = _get_patient_or_404(db, patient_id)

        if current_user.role == "admin":
            return patient

        if current_user.role == "patient":
            own = _get_patient_for_user(db, current_user.id)
            if not own or own.id != patient.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
            return patient

        if current_user.role == "doctor":
            doctor = _get_doctor_for_user(db, current_user.id)
            if not doctor or not _doctor_linked_to_patient(db, doctor.id, patient_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this patient dossier",
                )
            return patient

        if current_user.role in CLINICAL_STAFF_ROLES:
            cid = user_clinic_id(current_user)
            if cid and _clinic_linked_to_patient(db, cid, patient_id):
                return patient
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this patient dossier",
            )

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    @staticmethod
    def assert_can_write_clinical(
        db: Session, current_user: User, patient_id: int
    ) -> tuple[models.Patient, models.Doctor | None]:
        """Notes, summaries, and clinical documents — doctor, admin, or clinical staff at clinic."""
        patient = PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)

        if current_user.role == "admin":
            return patient, None

        if current_user.role == "doctor":
            doctor = _get_doctor_for_user(db, current_user.id)
            if not doctor:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Doctor profile not found",
                )
            return patient, doctor

        if current_user.role in ("lab_technician", "pharmacist", "receptionist"):
            return patient, None

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff can modify clinical records",
        )

    @staticmethod
    def resolve_doctor_id(db: Session, current_user: User, doctor: models.Doctor | None) -> int | None:
        if doctor is not None:
            return doctor.id
        if current_user.role == "admin":
            return None
        return None
