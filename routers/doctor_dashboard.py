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
    current_user=Depends(require_roles(["doctor", "admin"])),
):
    """Doctor: own appointments. Admin: recent appointments across all doctors (demo / oversight)."""

    def _serialize(appointment: models.RendezVous, admin_ctx: bool) -> dict:
        patient = appointment.patient
        patient_name = "Patient"
        if patient:
            full_name = f"{patient.first_name or ''} {patient.last_name or ''}".strip()
            patient_name = full_name or f"Patient #{patient.id}"

        row = {
            "id": appointment.id,
            "patient_name": patient_name,
            "date": appointment.date,
            "duration_minutes": appointment.duration_minutes,
            "status": appointment.status,
        }
        if admin_ctx and appointment.doctor:
            d = appointment.doctor
            row["doctor_name"] = f"{d.first_name or ''} {d.last_name or ''}".strip() or f"Dr #{d.id}"
        return row

    if current_user.role == "admin":
        appointments = (
            db.query(models.RendezVous)
            .order_by(models.RendezVous.date.desc())
            .limit(250)
            .all()
        )
        return [_serialize(a, True) for a in appointments]

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

    return [_serialize(a, False) for a in appointments]
