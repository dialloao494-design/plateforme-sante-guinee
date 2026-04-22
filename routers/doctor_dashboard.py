from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
from database import get_db
from security import require_roles

router = APIRouter(prefix="/doctor", tags=["Doctor Dashboard"])


@router.get("/appointments")
def get_doctor_appointments(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["doctor"])),
):
    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == current_user.id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )

    appointments = (
        db.query(models.RendezVous)
        .filter(models.RendezVous.doctor_id == doctor.id)
        .order_by(models.RendezVous.date.desc())
        .all()
    )

    result: List[dict] = []
    for appointment in appointments:
        patient = appointment.patient
        patient_name = "Patient"
        if patient:
            full_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
            patient_name = full_name or f"Patient #{patient.id}"

        result.append(
            {
                "id": appointment.id,
                "patient_name": patient_name,
                "date": appointment.date,
                "duration_minutes": appointment.duration_minutes,
                "status": appointment.status,
            }
        )

    return result
