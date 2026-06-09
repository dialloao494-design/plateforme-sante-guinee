import logging

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
import models
from database import get_db
from security import get_current_user, get_current_patient
from schemas import rendezvous as rendezvous_schemas
from services.rendezvous_service import RendezVousService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/appointments", tags=["Appointments"])


def _get_patient_for_user(db: Session, user_id: int) -> models.Patient | None:
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def _get_doctor_for_user(db: Session, user_id: int) -> models.Doctor | None:
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def _assert_can_access_appointment(db: Session, appointment: models.RendezVous, current_user) -> None:
    if current_user.role == "admin":
        return

    if current_user.role == "patient":
        patient = _get_patient_for_user(db, current_user.id)
        if not patient or appointment.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return

    if current_user.role == "doctor":
        doctor = _get_doctor_for_user(db, current_user.id)
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


@router.get("/", response_model=List[rendezvous_schemas.RendezVousWithParticipants])
def list_appointments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return appointments filtered by role.

    - Patients: only their own appointments
    - Doctors: only their own appointments
    - Admins: all appointments
    """
    RendezVousService.ensure_schema(db)
    return RendezVousService.list_appointments_for_user(current_user, db)


@router.get("/me", response_model=List[rendezvous_schemas.RendezVousWithParticipants])
def list_my_appointments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return appointments for the currently authenticated user."""
    RendezVousService.ensure_schema(db)
    return RendezVousService.list_appointments_for_user(current_user, db)


@router.post("/", response_model=rendezvous_schemas.RendezVousResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    rdv: rendezvous_schemas.RendezVousCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_patient),
):
    """
    Create a new appointment for the authenticated patient.
    """
    logger.info("Received POST /appointments/ request")
    logger.debug("Appointment payload: %s", rdv)

    RendezVousService.ensure_schema(db)

    patient = db.query(models.Patient).filter(
        models.Patient.user_id == current_user.id
    ).first()
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

    doctor = db.query(models.Doctor).filter(models.Doctor.id == rdv.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    appointment = RendezVousService.create_appointment(
        rdv=rdv,
        patient=patient,
        doctor=doctor,
        db=db
    )

    logger.info("Created appointment %s for patient_id=%s doctor_id=%s", appointment.id, patient.id, rdv.doctor_id)
    return appointment


@router.get("/{appointment_id}", response_model=rendezvous_schemas.RendezVousResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    RendezVousService.ensure_schema(db)
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, appointment, current_user)
    return appointment


@router.put("/{appointment_id}", response_model=rendezvous_schemas.RendezVousResponse)
def update_appointment(
    appointment_id: int,
    update: rendezvous_schemas.RendezVousUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not update.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required")

    RendezVousService.ensure_schema(db)
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, appointment, current_user)

    # Patients can only cancel their own appointments.
    if current_user.role == "patient" and update.status != "cancelled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    from core.payment_access_policy import PaymentAccessPolicy

    PaymentAccessPolicy.assert_status_transition_allowed(appointment, update.status)

    return RendezVousService.update_appointment_status(
        rdv_id=appointment_id,
        new_status=update.status,
        db=db,
    )


@router.delete("/{appointment_id}", response_model=rendezvous_schemas.RendezVousResponse)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    RendezVousService.ensure_schema(db)
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if appointment.status == "cancelled":
        _assert_can_access_appointment(db, appointment, current_user)
        return appointment

    _assert_can_access_appointment(db, appointment, current_user)
    return RendezVousService.cancel_appointment(appointment_id, db)


@router.post("/{appointment_id}/cancel", response_model=rendezvous_schemas.RendezVousResponse)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    RendezVousService.ensure_schema(db)
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, appointment, current_user)

    if appointment.status == "cancelled":
        return appointment

    return RendezVousService.cancel_appointment(appointment_id, db)
