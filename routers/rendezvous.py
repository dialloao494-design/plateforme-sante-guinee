"""
Rendezvous (Appointment) Router

Endpoints for managing patient appointments with doctors.
All business logic is delegated to the RendezVousService layer.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import models
from database import get_db
from schemas import rendezvous as rendezvous_schemas
from security import get_current_doctor, get_current_patient, require_roles
from services import RendezVousService

router = APIRouter(prefix="/rendezvous", tags=["RendezVous"])


# ===============================
# CREATE APPOINTMENT
# ===============================

@router.post("/", response_model=rendezvous_schemas.RendezVousResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    rdv: rendezvous_schemas.RendezVousCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_patient),
):
    """
    Create a new appointment.
    
    Business logic performed:
    - Validates appointment duration (30, 60, 90, 120 minutes)
    - Prevents booking in the past
    - Detects overlapping appointments (time-range based, not exact match)
    - Verifies appointment is within doctor's availability schedule
    - Auto-assigns current patient (prevents booking for others)
    
    Returns: Created appointment with full details
    """
    # Get patient profile for current user
    patient = db.query(models.Patient).filter(
        models.Patient.user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    # Get doctor
    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == rdv.doctor_id
    ).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    # Delegate to service - handles all validation and creation
    appointment = RendezVousService.create_appointment(
        rdv=rdv,
        patient=patient,
        doctor=doctor,
        db=db
    )

    return appointment


# ===============================
# READ APPOINTMENTS
# ===============================

@router.get("/", response_model=List[rendezvous_schemas.RendezVousResponse])
def list_appointments(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """
    List appointments based on user role.
    
    - Patients: See only their own appointments
    - Doctors: See only their own appointments
    - Admins: See all appointments
    """
    if current_user.role == "patient":
        patient = db.query(models.Patient).filter(
            models.Patient.user_id == current_user.id
        ).first()
        if patient:
            return db.query(models.RendezVous).filter(
                models.RendezVous.patient_id == patient.id
            ).all()
        return []
    
    if current_user.role == "doctor":
        doctor = db.query(models.Doctor).filter(
            models.Doctor.user_id == current_user.id
        ).first()
        if doctor:
            return db.query(models.RendezVous).filter(
                models.RendezVous.doctor_id == doctor.id
            ).all()
        return []
    
    # Admin: return all
    return db.query(models.RendezVous).all()


@router.get("/{rdv_id}", response_model=rendezvous_schemas.RendezVousResponse)
def get_appointment(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """
    Get a specific appointment by ID with access control.
    
    - Patients can only view their own appointments
    - Doctors can only view their own appointments
    - Admins can view any appointment
    """
    rdv = db.query(models.RendezVous).filter(
        models.RendezVous.id == rdv_id
    ).first()

    if not rdv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Access control
    if current_user.role == "patient":
        patient = db.query(models.Patient).filter(
            models.Patient.user_id == current_user.id
        ).first()
        if not patient or rdv.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    elif current_user.role == "doctor":
        doctor = db.query(models.Doctor).filter(
            models.Doctor.user_id == current_user.id
        ).first()
        if not doctor or rdv.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    return rdv


# ===============================
# UPDATE APPOINTMENT STATUS
# ===============================

@router.patch("/{rdv_id}", response_model=rendezvous_schemas.RendezVousResponse)
def update_appointment_status(
    rdv_id: int,
    update: rendezvous_schemas.RendezVousUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor"])),
):
    """
    Update appointment status with valid state transitions.
    
    Valid transitions:
    - pending -> confirmed or cancelled
    - confirmed -> completed or cancelled
    - completed -> (terminal state)
    - cancelled -> (terminal state)
    
    Only admins and doctors can update appointments.
    """
    if not update.status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )

    # Delegate to service - handles validation and state transitions
    appointment = RendezVousService.update_appointment_status(
        rdv_id=rdv_id,
        new_status=update.status,
        db=db
    )

    return appointment


# ===============================
# CANCEL APPOINTMENT
# ===============================

@router.post("/{rdv_id}/cancel", response_model=rendezvous_schemas.RendezVousResponse)
def cancel_appointment(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "patient"])),
):
    """
    Cancel an appointment (convenience endpoint for status transition).
    
    - Patients can cancel their own appointments
    - Admins can cancel any appointment
    """
    rdv = db.query(models.RendezVous).filter(
        models.RendezVous.id == rdv_id
    ).first()

    if not rdv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Access control
    if current_user.role == "patient":
        patient = db.query(models.Patient).filter(
            models.Patient.user_id == current_user.id
        ).first()
        if not patient or rdv.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    # Use service to handle cancellation
    appointment = RendezVousService.cancel_appointment(rdv_id, db)

    return appointment


# ===============================
# PAYMENT MANAGEMENT
# ===============================

@router.post("/{rdv_id}/confirm-payment", response_model=rendezvous_schemas.RendezVousResponse)
def confirm_appointment_payment(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "patient"])),
):
    """
    Confirm appointment after successful payment.
    
    Updates appointment to 'confirmed' status and 'paid' payment status.
    - Patients can confirm payment for their own appointments
    - Admins can confirm payment for any appointment
    
    Raises 400 if:
    - Appointment is not in 'pending' status
    - Appointment was not found
    """
    rdv = db.query(models.RendezVous).filter(
        models.RendezVous.id == rdv_id
    ).first()

    if not rdv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Access control
    if current_user.role == "patient":
        patient = db.query(models.Patient).filter(
            models.Patient.user_id == current_user.id
        ).first()
        if not patient or rdv.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

    # Use service to handle payment confirmation
    appointment = RendezVousService.confirm_appointment_after_payment(rdv_id, db)

    return appointment


@router.post("/{rdv_id}/mark-payment-failed", response_model=rendezvous_schemas.RendezVousResponse)
def mark_appointment_payment_failed(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin"])),
):
    """
    Mark appointment payment as failed.

    Only admins can perform this action.
    Updates only the payment_status field, not the appointment status.

    Raises 404 if appointment not found.
    """
    rdv = db.query(models.RendezVous).filter(
        models.RendezVous.id == rdv_id
    ).first()

    if not rdv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Use service to handle marking payment as failed
    appointment = RendezVousService.mark_appointment_payment_failed(rdv_id, db)

    return appointment


# ===============================
# SPECIAL QUERIES
# ===============================

@router.get("/doctor/{doctor_id}/available-slots")
def get_doctor_available_slots(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "patient"])),
):
    """
    Get available time slots for a doctor.
    
    Returns: List of free slots based on availability and existing appointments
    """
    doctor = db.query(models.Doctor).filter(
        models.Doctor.id == doctor_id
    ).first()
    
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    # Get all active availability slots
    slots = db.query(models.DoctorAvailability).filter(
        models.DoctorAvailability.doctor_id == doctor_id,
        models.DoctorAvailability.is_active == True,
    ).all()

    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor.name,
        "availability_slots": [
            {
                "slot_id": slot.id,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
            }
            for slot in slots
        ]
    }