from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models
import schemas
from database import get_db
from security import get_current_admin, require_roles

router = APIRouter(prefix="/patients", tags=["Patients"])


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
        gender=patient.gender
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


@router.get("/", response_model=List[schemas.PatientResponse])
def get_patients(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["doctor"])),
):
    return db.query(models.Patient).all()


@router.get("/{patient_id}", response_model=schemas.PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["doctor"])),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.delete("/{patient_id}")
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    db.delete(patient)
    db.commit()
    return {"detail": "Patient deleted successfully"}


@router.put("/{patient_id}", response_model=schemas.PatientResponse)
def update_patient(
    patient_id: int,
    patient_update: schemas.PatientCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_admin),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.user_id = patient_update.user_id
    patient.first_name = patient_update.first_name
    patient.last_name = patient_update.last_name
    patient.age = patient_update.age
    patient.gender = patient_update.gender
    db.commit()
    db.refresh(patient)
    return patient


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
    return patient