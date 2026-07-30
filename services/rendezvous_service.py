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
from sqlalchemy import inspect, text
from fastapi import HTTPException, status
import os

import models
from core.roles import effective_role
from schemas import rendezvous as rendezvous_schemas


def _cmp_dt(dt: datetime) -> datetime:
    """Normalize for comparisons between naive (browser) and aware (ISO API) datetimes."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


class RendezVousService:
    """Service for managing appointment lifecycle and business logic"""

    # Temporary MVP switch: bypass doctor availability table checks (dev/staging only).
    # Blocked in production by core.settings.validate_production_boot().
    BYPASS_AVAILABILITY_VALIDATION = os.getenv("BYPASS_AVAILABILITY_VALIDATION", "false").lower() == "true"

    # Production mode: availability and conflict checks are enabled.
    DEV_MODE = False

    # Minimum duration in minutes
    MIN_DURATION_MINUTES = 15

    @staticmethod
    def ensure_schema(db: Session) -> None:
        """Best-effort schema patch for existing DBs without migrations."""
        try:
            inspector = inspect(db.bind)
            if "rendezvous" not in inspector.get_table_names():
                return

            columns = {col["name"] for col in inspector.get_columns("rendezvous")}
            statements = []

            if "consultation_type" not in columns:
                statements.append("ALTER TABLE rendezvous ADD COLUMN consultation_type VARCHAR DEFAULT 'physical'")
            if "meeting_link" not in columns:
                statements.append("ALTER TABLE rendezvous ADD COLUMN meeting_link VARCHAR")

            for stmt in statements:
                db.execute(text(stmt))

            if statements:
                db.commit()
        except Exception:
            db.rollback()
    
    # Patient portal workflow: pending → confirmed → checked_in → completed (or cancelled).
    VALID_TRANSITIONS = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["checked_in", "completed", "cancelled"],
        "checked_in": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
        # legacy aliases kept for existing rows
        "paid": ["confirmed", "cancelled"],
        "confirmé": ["checked_in", "completed", "cancelled"],
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
        if rdv.duration_minutes < RendezVousService.MIN_DURATION_MINUTES:
            validation_errors.append(
                f"Invalid duration. Minimum allowed is {RendezVousService.MIN_DURATION_MINUTES} minutes"
            )

        # 2. Prevent booking in the past
        # Note: naive datetimes from datetime-local; aware datetimes from ISO clients
        now = datetime.now(rdv.date.tzinfo) if rdv.date.tzinfo else datetime.now()
        if _cmp_dt(rdv.date) < _cmp_dt(now):
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

        # 4. Prevent exact double-booking at the same date/time for the same doctor.
        exact_conflict = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.doctor_id == doctor.id,
                models.RendezVous.status != "cancelled",
                models.RendezVous.date == rdv.date,
            )
            .first()
        )
        if exact_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce créneau est déjà réservé"
            )

        # 5. Check overlapping appointments.
        overlap = RendezVousService.check_overlap_with_duration(
            doctor_id=doctor.id,
            start_time=rdv.date,
            duration_minutes=rdv.duration_minutes,
            db=db,
            exclude_rdv_id=None
        )
        if overlap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce créneau est déjà réservé"
            )

        # 6. Check doctor's availability window (temporarily bypassed for MVP).
        availability_check = {"is_available": True, "slot": None, "reason": "bypassed"}
        if not RendezVousService.BYPASS_AVAILABILITY_VALIDATION:
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

        return {
            "valid": True,
            "availability_slot": availability_check['slot']
        }

    @staticmethod
    def list_appointments_for_user(current_user, db: Session):
        """Return appointments scoped according to user role."""
        RendezVousService.ensure_schema(db)

        role = effective_role(current_user.role)

        if role == "patient":
            patient = db.query(models.Patient).filter(
                models.Patient.user_id == current_user.id
            ).first()
            if not patient:
                return []
            return db.query(models.RendezVous).filter(
                models.RendezVous.patient_id == patient.id
            ).all()

        if role == "doctor":
            doctor = db.query(models.Doctor).filter(
                models.Doctor.user_id == current_user.id
            ).first()
            if not doctor:
                return []
            return db.query(models.RendezVous).filter(
                models.RendezVous.doctor_id == doctor.id
            ).all()

        if role in ("platform_admin", "platform_owner"):
            return db.query(models.RendezVous).all()

        if role in ("clinic_admin", "admin"):
            cid = current_user.clinic_id
            if cid is None:
                return []
            return db.query(models.RendezVous).filter(models.RendezVous.clinic_id == cid).all()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role for appointment access"
        )

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
            if _cmp_dt(start_time) < _cmp_dt(existing_end) and _cmp_dt(appt.date) < _cmp_dt(appointment_end):
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
        3. Create appointment record with default status "pending" and payment_status "unpaid"
        4. Commit to database
        5. Refresh and return
        """
        RendezVousService.ensure_schema(db)
        validation_result = RendezVousService.validate_appointment(rdv, patient, doctor, db)

        # Final guard before insert to reduce edge-case double booking on near-simultaneous requests.
        final_conflict = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.doctor_id == doctor.id,
                models.RendezVous.status != "cancelled",
                models.RendezVous.date == rdv.date,
            )
            .first()
        )
        if final_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce créneau est déjà réservé"
            )

        # Create appointment with price from doctor's consultation fee
        if not doctor.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor must belong to a clinic",
            )

        if patient.clinic_id is not None and patient.clinic_id != doctor.clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient belongs to another clinic",
            )

        # Fail closed: unbound patients (clinic_id NULL) cannot be silently claimed
        # via appointment creation — reception/admin must assign clinic first.
        if patient.clinic_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient is not assigned to a clinic",
            )

        new_rdv = models.RendezVous(
            date=rdv.date,
            duration_minutes=rdv.duration_minutes,
            patient_id=patient.id,
            doctor_id=doctor.id,
            clinic_id=doctor.clinic_id,
            status="pending",
            payment_status="unpaid",
            price=doctor.consultation_fee,
            consultation_type=rdv.consultation_type,
            clinical_status="scheduled",
        )

        from services.clinic_billing_service import ClinicBillingService

        db.add(new_rdv)
        db.flush()

        ClinicBillingService.create_consultation_charge(
            db,
            clinic_id=doctor.clinic_id,
            patient_id=patient.id,
            appointment_id=new_rdv.id,
            amount_gnf=int(doctor.consultation_fee or 150_000),
            description=f"Consultation — Dr. {doctor.name}",
        )

        # Teleconsult join URLs are never pre-generated before payment (R1).
        new_rdv.meeting_link = None

        db.commit()
        db.refresh(new_rdv)

        # Mark a matching availability slot unavailable if the appointment consumes it exactly.
        availability_slot = validation_result.get("availability_slot")
        if availability_slot:
            appointment_end = rdv.date + timedelta(minutes=rdv.duration_minutes)
            RendezVousService.reserve_availability_slot(availability_slot, rdv.date, appointment_end, db)

        if new_rdv.status not in ("cancelled",):
            from services.reminder_service import ReminderService

            ReminderService.schedule_for_appointment(db, new_rdv)

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
        - confirmed -> cancelled
        - cancelled -> (no further transitions)
        """
        RendezVousService.ensure_schema(db)
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

        from core.payment_access_policy import PaymentAccessPolicy

        PaymentAccessPolicy.assert_status_transition_allowed(rdv, new_status)

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
        db: Session,
        *,
        channel: str,
        actor_user_id: int | None = None,
        stub_token: str | None = None,
        stripe_payment_intent_id: str | None = None,
        stripe_session_id: str | None = None,
        amount_cents: int | None = None,
        currency: str = "eur",
        admin_reference: str | None = None,
    ) -> models.RendezVous:
        """
        Confirm an appointment after verified payment settlement.

        All callers must specify an authorized settlement ``channel``; see
        ``services.payment_settlement.PaymentSettlementService``.
        """
        from services.payment_settlement import PaymentSettlementService

        return PaymentSettlementService.settle_appointment(
            db,
            rdv_id,
            channel=channel,
            actor_user_id=actor_user_id,
            stub_token=stub_token,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_session_id=stripe_session_id,
            amount_cents=amount_cents,
            currency=currency,
            admin_reference=admin_reference,
        )

    @staticmethod
    def mark_appointment_payment_failed(
        rdv_id: int,
        db: Session
    ) -> models.RendezVous:
        """
        Mark appointment payment as unpaid.

        Only updates payment_status, not appointment status.

        Returns: Updated appointment
        """
        RendezVousService.ensure_schema(db)
        rdv = db.query(models.RendezVous).filter(models.RendezVous.id == rdv_id).first()

        if not rdv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )

        rdv.payment_status = "unpaid"
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
    def create_payment_intent(appointment_id: int, db: Session) -> dict:
        """Online card checkout removed — patients pay at reception (clinical billing)."""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Online payment is disabled; pay at clinic reception",
        )

    @staticmethod
    def handle_stripe_webhook(event: dict, db: Session) -> dict:
        """Legacy webhook handler removed with Stripe integration."""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Online payment webhooks are disabled",
        )
