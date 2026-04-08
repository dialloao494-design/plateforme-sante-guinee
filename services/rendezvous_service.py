"""
Rendezvous (Appointment) Service Layer

Handles all business logic for appointment management:
- Validation (dates, overlaps, availability)
- Creation with comprehensive checks
- Status transitions
- Conflict detection
"""

from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

import models
from schemas import rendezvous as rendezvous_schemas


class RendezVousService:
    """Service for managing appointment lifecycle and business logic"""

    # Valid appointment durations in minutes
    VALID_DURATIONS = [30, 60, 90, 120]
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["completed", "cancelled"],
        "completed": [],
        "cancelled": []
    }

    @staticmethod
    def validate_appointment(
        rdv: rendezvous_schemas.RendezVousCreate,
        patient: models.Patient,
        doctor: models.Doctor,
        db: Session
    ) -> dict:
        """
        Comprehensive appointment validation.
        
        Checks:
        1. Appointment duration is valid (30, 60, 90, 120 minutes)
        2. Appointment is not in the past
        3. Doctor exists
        4. No overlapping appointments (excluding cancelled appointments)
        5. Appointment is within doctor's availability window
        6. Cannot book if a confirmed or running appointment exists for same slot
        
        Raises HTTPException if validation fails.
        Returns validation details if successful.
        """
        validation_errors = []

        # 1. Validate duration
        if rdv.duration_minutes not in RendezVousService.VALID_DURATIONS:
            validation_errors.append(
                f"Invalid duration. Must be one of: {RendezVousService.VALID_DURATIONS}"
            )

        # 2. Prevent booking in the past
        if rdv.date < datetime.utcnow():
            validation_errors.append("Cannot book appointments in the past")

        # 3. Verify doctor exists (should already be done but double-check)
        if not doctor:
            validation_errors.append("Doctor not found")

        # If we have validation errors so far, raise immediately
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=" | ".join(validation_errors)
            )

        # 4. Check for overlapping appointments
        overlap = RendezVousService.check_overlap_with_duration(
            doctor_id=doctor.id,
            start_time=rdv.date,
            duration_minutes=rdv.duration_minutes,
            db=db,
            exclude_rdv_id=None  # New appointment, nothing to exclude
        )
        if overlap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Time slot conflicts with existing appointment (ID: {overlap['id']}, "
                       f"starts {overlap['date']}, duration {overlap['duration_minutes']} min)"
            )

        # 5. Check if appointment is within doctor's availability
        availability_check = RendezVousService.is_within_availability(
            doctor=doctor,
            appointment_start=rdv.date,
            duration_minutes=rdv.duration_minutes,
            db=db
        )
        if not availability_check['is_available']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No availability for doctor at this time. {availability_check['reason']}"
            )

        # 6. Prevent booking if confirmed/completed appointment already exists at this time
        existing_confirmed = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.doctor_id == doctor.id,
                models.RendezVous.status.in_(["confirmed", "completed"]),
                models.RendezVous.date == rdv.date,
                models.RendezVous.duration_minutes == rdv.duration_minutes
            )
            .first()
        )
        if existing_confirmed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot book appointment: Doctor already has a {existing_confirmed.status} appointment at this time"
            )

        return {
            "valid": True,
            "availability_slot": availability_check['slot']
        }

    @staticmethod
    def list_appointments_for_user(current_user, db: Session):
        """Return appointments scoped according to user role."""
        if current_user.role == "patient":
            patient = db.query(models.Patient).filter(
                models.Patient.user_id == current_user.id
            ).first()
            if not patient:
                return []
            return db.query(models.RendezVous).filter(
                models.RendezVous.patient_id == patient.id
            ).all()

        if current_user.role == "doctor":
            doctor = db.query(models.Doctor).filter(
                models.Doctor.user_id == current_user.id
            ).first()
            if not doctor:
                return []
            return db.query(models.RendezVous).filter(
                models.RendezVous.doctor_id == doctor.id
            ).all()

        return db.query(models.RendezVous).all()

    @staticmethod
    def list_payments_for_user(current_user, db: Session):
        """Return payment-related appointments scoped by role."""
        return RendezVousService.list_appointments_for_user(current_user, db)

    @staticmethod
    def check_overlap_with_duration(
        doctor_id: int,
        start_time: datetime,
        duration_minutes: int,
        db: Session,
        exclude_rdv_id: int = None
    ) -> dict | None:
        """
        Smart overlap detection using time ranges.
        
        An appointment is considered overlapping if:
        - It's for the same doctor
        - Status is not 'cancelled'
        - Time ranges intersect (not just exact match)
        
        Time overlap formula:
        - New appointment: [start_time, start_time + duration]
        - Existing: [existing.date, existing.date + duration]
        - Overlap if: new_start < existing_end AND existing_start < new_end
        
        Returns the overlapping appointment dict if conflict exists, None otherwise.
        """
        appointment_end = start_time + timedelta(minutes=duration_minutes)

        # Find all non-cancelled appointments for this doctor
        appointments = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.doctor_id == doctor_id,
                models.RendezVous.status != "cancelled"
            )
            .all()
        )

        for appt in appointments:
            # Skip the appointment we're potentially updating
            if exclude_rdv_id and appt.id == exclude_rdv_id:
                continue

            existing_end = appt.date + timedelta(minutes=appt.duration_minutes)

            # Check for overlap: new_start < existing_end AND existing_start < new_end
            if start_time < existing_end and appt.date < appointment_end:
                return {
                    "id": appt.id,
                    "date": appt.date,
                    "duration_minutes": appt.duration_minutes
                }

        return None

    @staticmethod
    def is_within_availability(
        doctor: models.Doctor,
        appointment_start: datetime,
        duration_minutes: int,
        db: Session
    ) -> dict:
        """
        Verify appointment is within doctor's working hours availability.
        
        Requirements:
        - Doctor must have a working hours slot for the appointment's day of week
        - Appointment start time must be >= working hours start_time
        - Appointment end time must be <= working hours end_time
        
        Args:
            doctor: Doctor model instance
            appointment_start: datetime of appointment start
            duration_minutes: duration of appointment in minutes
            db: Database session
            
        Returns dict with:
        - is_available: bool
        - slot: DoctorAvailability object if available
        - reason: str explanation if not available
        """
        from datetime import time
        
        appointment_end = appointment_start + timedelta(minutes=duration_minutes)
        appointment_day = appointment_start.weekday()  # 0 = Monday, 6 = Sunday
        appointment_start_time = appointment_start.time()
        appointment_end_time = appointment_end.time()

        # Find active availability slot for this day of week
        availability_slot = (
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor.id,
                models.DoctorAvailability.day_of_week == appointment_day,
                models.DoctorAvailability.is_active == True,
            )
            .first()
        )

        if not availability_slot:
            reason = f"Doctor has no working hours scheduled for {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][appointment_day]}"
            return {
                "is_available": False,
                "slot": None,
                "reason": reason
            }

        # Check if appointment time falls within working hours
        # Handle case where appointment spans across midnight (shouldn't normally happen but be safe)
        if (availability_slot.start_time <= appointment_start_time and 
            appointment_end_time <= availability_slot.end_time):
            return {
                "is_available": True,
                "slot": availability_slot,
                "reason": ""
            }

        # Appointment falls outside working hours
        reason = (
            f"Appointment {appointment_start_time.strftime('%H:%M')} - {appointment_end_time.strftime('%H:%M')} "
            f"falls outside working hours {availability_slot.start_time.strftime('%H:%M')} - {availability_slot.end_time.strftime('%H:%M')}"
        )
        return {
            "is_available": False,
            "slot": None,
            "reason": reason
        }

    @staticmethod
    def create_appointment(
        rdv: rendezvous_schemas.RendezVousCreate,
        patient: models.Patient,
        doctor: models.Doctor,
        db: Session
    ) -> models.RendezVous:
        """
        Create appointment with full validation.
        
        Steps:
        1. Validate all business rules
        2. Set price from doctor's consultation fee
        3. Create appointment record with default status "pending" and payment_status "pending"
        4. Commit to database
        5. Refresh and return
        """
        # Comprehensive validation
        RendezVousService.validate_appointment(rdv, patient, doctor, db)

        validation_result = RendezVousService.validate_appointment(rdv, patient, doctor, db)

        # Create appointment with price from doctor's consultation fee
        new_rdv = models.RendezVous(
            date=rdv.date,
            duration_minutes=rdv.duration_minutes,
            patient_id=patient.id,
            doctor_id=doctor.id,
            status="pending",
            payment_status="pending",
            price=doctor.consultation_fee,
        )

        db.add(new_rdv)
        db.commit()
        db.refresh(new_rdv)

        # Mark a matching availability slot unavailable if the appointment consumes it exactly.
        availability_slot = validation_result.get("availability_slot")
        if availability_slot:
            appointment_end = rdv.date + timedelta(minutes=rdv.duration_minutes)
            RendezVousService.reserve_availability_slot(availability_slot, rdv.date, appointment_end, db)

        return new_rdv

    @staticmethod
    def reserve_availability_slot(
        availability_slot: models.DoctorAvailability,
        appointment_start: datetime,
        appointment_end: datetime,
        db: Session,
    ) -> None:
        """Mark the exact availability slot unavailable after booking."""
        if not availability_slot:
            return

        if (
            availability_slot.start_time == appointment_start.time()
            and availability_slot.end_time == appointment_end.time()
        ):
            availability_slot.is_active = False
            db.commit()
            db.refresh(availability_slot)

    @staticmethod
    def update_appointment_status(
        rdv_id: int,
        new_status: str,
        db: Session
    ) -> models.RendezVous:
        """
        Update appointment status with valid state transitions.
        
        Valid transitions:
        - pending -> confirmed or cancelled
        - confirmed -> completed or cancelled
        - completed -> (no further transitions)
        - cancelled -> (no further transitions)
        """
        rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
        
        if not rdv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )

        # Validate status value
        if new_status not in RendezVousService.VALID_TRANSITIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {list(RendezVousService.VALID_TRANSITIONS.keys())}"
            )

        # Validate status transition
        allowed_next_states = RendezVousService.VALID_TRANSITIONS[rdv.status]
        if new_status not in allowed_next_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition from '{rdv.status}' to '{new_status}'. "
                       f"Allowed transitions: {allowed_next_states}"
            )

        rdv.status = new_status
        rdv.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rdv)

        return rdv

    @staticmethod
    def cancel_appointment(rdv_id: int, db: Session) -> models.RendezVous:
        """Cancel an appointment (convenience method for status update)"""
        return RendezVousService.update_appointment_status(rdv_id, "cancelled", db)

    @staticmethod
    def confirm_appointment_after_payment(
        rdv_id: int,
        db: Session
    ) -> models.RendezVous:
        """
        Confirm an appointment after successful payment.
        
        Updates:
        - Sets appointment status to 'confirmed' (only from 'pending')
        - Sets payment_status to 'paid'
        - Updates timestamp
        
        Raises HTTPException if:
        - Appointment not found
        - Appointment is not in 'pending' status
        - Price is 0 (free appointments should be auto-confirmed)
        
        Returns: Updated appointment
        """
        rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()
        
        if not rdv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Check if appointment is in pending status
        if rdv.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm payment for appointment with status '{rdv.status}'. Only pending appointments can be confirmed via payment."
            )
        
        # Update appointment status after payment
        rdv.status = "confirmed"
        rdv.payment_status = "paid"
        rdv.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(rdv)
        
        return rdv

    @staticmethod
    def mark_appointment_payment_failed(
        rdv_id: int,
        db: Session
    ) -> models.RendezVous:
        """
        Mark appointment payment as failed.

        Only updates payment_status, not appointment status.

        Returns: Updated appointment
        """
        rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()

        if not rdv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )

        rdv.payment_status = "failed"
        rdv.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(rdv)

        return rdv

    @staticmethod
    def get_appointment_duration_string(duration_minutes: int) -> str:
        """Convert minutes to human-readable duration"""
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        
        if hours == 0:
            return f"{minutes} min"
        elif minutes == 0:
            return f"{hours} h"
        else:
            return f"{hours} h {minutes} min"

    @staticmethod
    def create_payment_intent(
        appointment_id: int,
        db: Session
    ) -> dict:
        """
        Create a Stripe payment intent for an appointment.
        
        Called when a patient initiates payment for an appointment.
        Does NOT confirm the appointment - confirmation happens after successful payment.
        
        Args:
            appointment_id: ID of the appointment to create payment for
            db: Database session
            
        Returns:
            Dict with client_secret and payment intent details
            
        Raises:
            HTTPException if appointment not found or payment creation fails
        """
        from services.stripe_service import StripeService
        
        appointment = db.query(models.RendezVous).filter(
            models.RendezVous.id == appointment_id
        ).first()
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        
        # Prevent creating payment intent for already completed payment or cancelled appointments
        if appointment.payment_status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment has already been made for this appointment"
            )

        if appointment.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create payment intent for a cancelled appointment"
            )
        
        # Get patient and doctor info for payment intent
        patient = db.query(models.Patient).filter(
            models.Patient.id == appointment.patient_id
        ).first()
        
        doctor = db.query(models.Doctor).filter(
            models.Doctor.id == appointment.doctor_id
        ).first()
        
        if not patient or not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient or doctor not found"
            )
        
        patient_name = " ".join(
            filter(None, [patient.first_name, patient.last_name])
        ).strip() or (patient.user.email if patient.user else "Patient")

        # Create Stripe payment intent
        payment_intent = StripeService.create_payment_intent(
            appointment_id=appointment_id,
            appointment_price=appointment.price,
            patient_email=patient.user.email if patient.user else "patient@example.com",
            patient_name=patient_name,
            doctor_name=doctor.name,
            appointment_date=appointment.date.isoformat(),
            db=db
        )
        
        return payment_intent

    @staticmethod
    def handle_stripe_webhook(
        event: dict,
        db: Session
    ) -> dict:
        """
        Handle Stripe webhook events.
        
        Processes payment status changes:
        - payment_intent.succeeded: Confirm appointment and mark as paid
        - payment_intent.payment_failed: Mark as failed
        
        Args:
            event: Parsed Stripe webhook event
            db: Database session
            
        Returns:
            Dict with webhook processing result
            
        Raises:
            HTTPException on validation errors
        """
        from services.stripe_service import StripeService
        
        return StripeService.handle_webhook_event(event, db)
