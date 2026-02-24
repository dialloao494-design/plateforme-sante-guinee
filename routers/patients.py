uvicorn main:app --reloadfrom fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


@router.get("/")
def get_patients(db: Session = Depends(get_db)):
    return db.query(models.Patient).all()


@router.post("/", response_model=PatientResponse)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    new_patient = models.Patient(**patient.model_dump())
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


@router.get("/", response_model=list[PatientResponse])
def get_patients(db: Session = Depends(get_db)):
    return db.query(models.Patient).all()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.nom = updated_patient.nom
    patient.prenom = updated_patient.prenom
    patient.age = updated_patient.age
    patient.sexe = updated_patient.sexe

    db.commit()
    db.refresh(patient)

    return patient


@router.delete("/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.delete(patient)
    db.commit()

    return {"message": "Patient deleted"}