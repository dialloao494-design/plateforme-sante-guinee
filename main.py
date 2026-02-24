from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from database import engine
from models import Base
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Patient as PatientModel
from fastapi import Depends
app = FastAPI()
Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# ====== MODELE ======
class Patient(BaseModel):
    nom: str
    prenom: str
    age: int
    sexe: str

# ====== "BASE DE DONNÉES" TEMPORAIRE ======



# ====== ROUTES ======

@app.get("/")
def home():
    return {"message": "Plateforme Santé Guinée API en ligne"}

@app.post("/patients")
def create_patient(patient: Patient, db: Session = Depends(get_db)):
    new_patient = PatientModel(
        nom=patient.nom,
        prenom=patient.prenom,
        age=patient.age,
        sexe=patient.sexe
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    return new_patient

@app.get("/patients")
def get_patients(db: Session = Depends(get_db)):
    patients = db.query(PatientModel).all()
    return patients

 
 # create endpoint to delete patient
@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.id == patient_id).first()

    if not patient:
        return {"message": "Patient not found"}

    db.delete(patient)
    db.commit()

    return {"message": "Patient deleted successfully"}
from fastapi import HTTPException
@app.put("/patients/{patient_id}")
def update_patient(patient_id: int, updated_patient: Patient, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.id == patient_id).first()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient.nom = updated_patient.nom
    patient.prenom = updated_patient.prenom
    patient.age = updated_patient.age
    patient.sexe = updated_patient.sexe

    db.commit()
    db.refresh(patient)

    return patient