"""
Rendezvous (Appointment) Router

Endpoints for managing appointments with strict RBAC.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

import models
from database import get_db
from schemas import rendezvous as rendezvous_schemas
from security import get_current_user, require_roles
from services import RendezVousService

router = APIRouter(prefix="/rendezvous", tags=["RendezVous"])


def _get_patient_for_user(db: Session, user_id: int) -> models.Patient | None:
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def _get_or_create_patient_for_user(db: Session, user_id: int) -> models.Patient:
    patient = _get_patient_for_user(db, user_id)
    if patient:
        return patient

    patient = models.Patient(
        user_id=user_id,
        first_name="Patient",
        last_name=f"User{user_id}",
        age=0,
        gender="unknown",
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def _get_doctor_for_user(db: Session, user_id: int) -> models.Doctor | None:
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def _assert_can_access_appointment(db: Session, appointment: models.RendezVous, current_user) -> None:
    if current_user.role == "admin":
        return

    if current_user.role == "patient":
        patient = _get_or_create_patient_for_user(db, current_user.id)
        if appointment.patient_id != patient.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    if current_user.role == "doctor":
        doctor = _get_doctor_for_user(db, current_user.id)
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("/", response_model=rendezvous_schemas.RendezVousResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    rdv: rendezvous_schemas.RendezVousCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create appointment (patient only)."""
    if current_user.role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can create appointments"
        )

    patient = _get_or_create_patient_for_user(db, current_user.id)

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
    return appointment


@router.get("/", response_model=List[rendezvous_schemas.RendezVousResponse])
def list_appointments(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """List appointments for current user scope."""
    return RendezVousService.list_appointments_for_user(current_user, db)


@router.get("/{rdv_id}", response_model=rendezvous_schemas.RendezVousResponse)
def get_appointment(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """Get one appointment with ownership checks."""
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, rdv, current_user)
    return rdv


@router.patch("/{rdv_id}", response_model=rendezvous_schemas.RendezVousResponse)
def update_appointment_status(
    rdv_id: int,
    update: rendezvous_schemas.RendezVousUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor"])),
):
    """Update appointment status (doctor/admin only).
    
    SECURITY GATE: Cannot confirm appointment unless payment_status='paid'
    """
    if not update.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status is required")

    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    # Doctors can only modify appointments assigned to them.
    if current_user.role == "doctor":
        doctor = _get_doctor_for_user(db, current_user.id)
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # PAYMENT GATE: unified policy (same rules as PUT /appointments)
    from core.payment_access_policy import PaymentAccessPolicy

    PaymentAccessPolicy.assert_status_transition_allowed(appointment, update.status)

    return RendezVousService.update_appointment_status(rdv_id=rdv_id, new_status=update.status, db=db)


@router.post("/{rdv_id}/cancel", response_model=rendezvous_schemas.RendezVousResponse)
def cancel_appointment(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "patient", "doctor"])),
):
    """Cancel appointment with role rules.

    - Patient: can cancel only own future appointments
    - Doctor: can cancel own assigned appointments anytime
    - Admin: can cancel any appointment
    """
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, rdv, current_user)

    if current_user.role == "patient" and rdv.date <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patients can only cancel appointments before the appointment time"
        )

    return RendezVousService.cancel_appointment(rdv_id, db)


@router.post("/{rdv_id}/confirm-payment", response_model=rendezvous_schemas.RendezVousResponse)
def confirm_appointment_payment(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin"])),
):
    """
    Admin-only manual settlement for legacy portal appointments.

    Patients pay at clinic reception via ``POST /clinical/billing/charges/{id}/pay``.
    """
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    _assert_can_access_appointment(db, rdv, current_user)

    from core.payment_policy import SETTLEMENT_CHANNEL_ADMIN_MANUAL
    from services.payment_settlement import PaymentSettlementService

    return PaymentSettlementService.settle_appointment(
        db,
        rdv_id,
        channel=SETTLEMENT_CHANNEL_ADMIN_MANUAL,
        actor_user_id=current_user.id,
        admin_reference="rendezvous-confirm-payment",
    )


@router.post("/{rdv_id}/mark-payment-failed", response_model=rendezvous_schemas.RendezVousResponse)
def mark_appointment_payment_failed(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin"])),
):
    """Mark appointment payment as unpaid (admin only)."""
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    return RendezVousService.mark_appointment_payment_failed(rdv_id, db)


@router.get("/doctor/{doctor_id}/available-slots")
def get_doctor_available_slots(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """Get active availability slots for a doctor."""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    slots = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == doctor_id,
        models.DoctorAvailability.is_active == True,
    ).all()

    return {
        "doctor_id": doctor_id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "availability_slots": [
            {
                "slot_id": slot.id,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
            }
            for slot in slots
        ]
    }
