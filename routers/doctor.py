# FastAPI router for Doctor CRUD with SQLAlchemy
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import doctor
from models.doctor import Doctor
from schemas.doctor import DoctorResponse
from fastapi import HTTPException
from schemas.doctor import DoctorCreate
from fastapi import Depends
from security import oauth2_scheme
from jose import jwt

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)

def get_db():
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD operations for Doctor
from pydantic import BaseModel


class DoctorBase(BaseModel):
    name: str
    specialty: str


@router.post("/")
def create_doctor(doctor: DoctorCreate, db: Session = Depends(get_db)):
    new_doctor = Doctor(
        name=doctor.name,
        specialty=doctor.specialty
    )
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    return new_doctor

@router.get("/")
def get_doctors(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    return db.query(Doctor).all()

@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(doctor_id: int, doctor_update: DoctorCreate, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor.name = doctor_update.name
    doctor.specialty = doctor_update.specialty
    db.commit()
    db.refresh(doctor)
    return doctor

@router.delete("/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    db.delete(doctor)
    db.commit()
    return {"detail": "Doctor deleted successfully"}
