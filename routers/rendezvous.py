from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models
from database import SessionLocal
from schemas import rendezvous as rendezvous_schemas

router = APIRouter(prefix="/rendezvous", tags=["RendezVous"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=rendezvous_schemas.RendezVousResponse)
def create_rendezvous(
    rdv: rendezvous_schemas.RendezVousCreate,
    db: Session = Depends(get_db),
):
    new_rdv = models.RendezVous(
        date=rdv.date,
        patient_id=rdv.patient_id,
        doctor_id=rdv.doctor_id,
    )

    db.add(new_rdv)
    db.commit()
    db.refresh(new_rdv)

    return new_rdv


@router.get("/", response_model=List[rendezvous_schemas.RendezVousResponse])
def get_rendezvous(db: Session = Depends(get_db)):
    return db.query(models.RendezVous).all()


@router.get("/{rdv_id}", response_model=rendezvous_schemas.RendezVousResponse)
def get_rendezvous_by_id(rdv_id: int, db: Session = Depends(get_db)):
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()

    if not rdv:
        raise HTTPException(status_code=404, detail="RendezVous not found")

    return rdv


@router.delete("/{rdv_id}")
def delete_rendezvous(rdv_id: int, db: Session = Depends(get_db)):
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()

    if not rdv:
        raise HTTPException(status_code=404, detail="RendezVous not found")

    db.delete(rdv)
    db.commit()

    return {"detail": "RendezVous deleted successfully"}