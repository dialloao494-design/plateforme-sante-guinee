from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import get_db
from security import get_current_admin, require_roles
from services.patient_record_service import PatientRecordService

router = APIRouter(prefix="/patients", tags=["Patients"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _doctor_for_user(db: Session, user_id: int) -> models.Doctor | None:
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def _assert_doctor_can_access_patient(db: Session, current_user, patient_id: int) -> None:
    doctor = _doctor_for_user(db, current_user.id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found")
    linked = (
        db.query(models.RendezVous)
        .filter(
            models.RendezVous.doctor_id == doctor.id,
            models.RendezVous.patient_id == patient_id,
        )
        .first()
    )
    if not linked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this patient",
        )


@router.post("/", response_model=schemas.PatientResponse)
def create_patient(
    patient: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    new_patient = models.Patient(
        user_id=patient.user_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        age=patient.age,
        gender=patient.gender,
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    from services.medical_history_service import ensure_medical_record

    ensure_medical_record(db, new_patient.id)
    return new_patient


@router.get("/", response_model=List[schemas.PatientResponse])
def get_patients(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["doctor", "admin"])),
):
    if current_user.role == "admin":
        return db.query(models.Patient).all()

    doctor = _doctor_for_user(db, current_user.id)
    if not doctor:
        return []

    patient_ids = [
        row[0]
        for row in db.query(models.RendezVous.patient_id)
        .filter(models.RendezVous.doctor_id == doctor.id)
        .distinct()
        .all()
    ]
    if not patient_ids:
        return []
    return db.query(models.Patient).filter(models.Patient.id.in_(patient_ids)).all()


@router.get("/me", response_model=schemas.PatientResponse)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["patient"])),
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = models.Patient(
            user_id=current_user.id,
            first_name="Patient",
            last_name=f"User{current_user.id}",
            age=0,
            gender="unknown",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
    else:
        changed = False
        if patient.first_name is None:
            patient.first_name = "Patient"
            changed = True
        if patient.last_name is None:
            patient.last_name = f"User{current_user.id}"
            changed = True
        if patient.age is None:
            patient.age = 0
            changed = True
        if patient.gender is None:
            patient.gender = "unknown"
            changed = True
        if changed:
            db.commit()
            db.refresh(patient)
    from services.medical_history_service import ensure_medical_record

    ensure_medical_record(db, patient.id)
    return patient


@router.get("/{patient_id}", response_model=schemas.PatientResponse)
def get_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["doctor", "admin", "patient"])),
):
    return PatientRecordService.get_patient_detail(
        db, patient_id, current_user, client_ip=_client_ip(request)
    )


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    has_clinical = (
        db.query(models.ClinicalConsultation)
        .filter(models.ClinicalConsultation.patient_id == patient_id)
        .first()
    )
    if has_clinical:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete patient with clinical history. Archive only.",
        )
    patient.is_archived = True
    patient.archived_at = datetime.utcnow()
    db.commit()
    return {"detail": "Patient archived successfully"}


@router.put("/{patient_id}", response_model=schemas.PatientResponse)
def update_patient(
    patient_id: int,
    patient_update: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor"])),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if current_user.role == "doctor":
        _assert_doctor_can_access_patient(db, current_user, patient_id)
        patient.first_name = patient_update.first_name
        patient.last_name = patient_update.last_name
        patient.age = patient_update.age
        patient.gender = patient_update.gender
    else:
        patient.user_id = patient_update.user_id
        patient.first_name = patient_update.first_name
        patient.last_name = patient_update.last_name
        patient.age = patient_update.age
        patient.gender = patient_update.gender

    db.commit()
    db.refresh(patient)
    return patient
