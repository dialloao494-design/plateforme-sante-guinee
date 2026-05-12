"""
Payments Router

Handles payment endpoints for appointments:
- Creating Stripe payment intents
- Processing Stripe webhooks
- Managing payment status

All business logic is delegated to RendezVousService and StripeService.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from database import get_db
import models
from security import get_current_admin, get_current_doctor, get_current_patient, require_roles
from services.rendezvous_service import RendezVousService
from services.stripe_service import StripeService
from schemas import rendezvous as rendezvous_schemas

router = APIRouter(prefix="/payments", tags=["Payments"])


def _get_or_create_patient_profile(db: Session, user_id: int) -> models.Patient:
    patient = db.query(models.Patient).filter(
        models.Patient.user_id == user_id
    ).first()
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


# ===============================
# CHECKOUT SESSION CREATION
# ===============================

@router.post("/create-intent", response_model=rendezvous_schemas.CheckoutSessionResponse)
def create_payment_intent(
    request: rendezvous_schemas.PaymentIntentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_patient),
):
    """
    Create a Stripe Checkout session for an appointment.

    - Creates hosted Stripe checkout page URL
    - Stores payment linkage in the appointment/payment tables
    - Does NOT confirm the appointment yet (confirmation requires Stripe validation)
    - Patient must own the appointment
    """
    # Get patient profile
    patient = _get_or_create_patient_profile(db, current_user.id)

    # Verify patient owns this appointment
    appointment = db.query(models.RendezVous).filter(
        models.RendezVous.id == request.appointment_id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    if appointment.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: This is not your appointment"
        )

    # Create checkout session via service
    payment_intent = RendezVousService.create_payment_intent(request.appointment_id, db)

    return payment_intent


@router.post("/confirm-checkout", response_model=rendezvous_schemas.RendezVousResponse)
def confirm_checkout_payment(
    payload: rendezvous_schemas.CheckoutSessionConfirmRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_patient),
):
    """Confirm payment after successful Stripe Checkout redirection.

    Security:
    - Session is revalidated server-side against Stripe
    - Appointment is confirmed only if Stripe reports payment_status=paid
    - Patient can confirm only their own appointment
    """
    appointment = StripeService.confirm_checkout_session(
        session_id=payload.session_id,
        db=db,
        expected_patient_user_id=current_user.id,
    )

    return appointment


@router.post("/{rdv_id}/confirm-payment", response_model=rendezvous_schemas.RendezVousResponse)
def confirm_payment_simple(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_patient),
):
    """
    Mark appointment as paid AND CONFIRMED (simple payment confirmation endpoint).
    
    Security:
    - Patient can only mark their own appointment as paid
    - Cannot confirm payment for cancelled appointments
    - Cannot confirm payment for already confirmed appointments
    - Sets payment_status to 'paid'
    - Sets status to 'confirmed' (CRITICAL: Must update both fields)
    
    This is used by frontend to finalize payment after backend validates it.
    
    Backend Truth Rules:
    - After successful payment, appointment MUST be confirmed
    - Status transitions: pending -> paid -> confirmed
    - Both fields must be updated atomically
    """
    patient = _get_or_create_patient_profile(db, current_user.id)
    
    appointment = db.query(models.RendezVous).filter(
        models.RendezVous.id == rdv_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    if appointment.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: This is not your appointment"
        )
    
    # Business rule: Cannot pay for cancelled appointments
    if appointment.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot confirm payment for cancelled appointment"
        )
    
    # Business rule: Cannot pay for already confirmed appointments
    if appointment.status == "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment already confirmed"
        )
    
    # CRITICAL FIX: Update BOTH payment_status AND status
    # This ensures backend truth: confirmed appointment = paid + confirmed status
    appointment.payment_status = "paid"
    appointment.status = "confirmed"
    appointment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(appointment)
    
    return appointment


# ===============================
# STRIPE WEBHOOK
# ===============================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook events.

    Stripe sends webhook notifications for payment events:
    - payment_intent.succeeded: Payment successful → confirm appointment
    - payment_intent.payment_failed: Payment failed → mark as failed

    Security:
    - Verifies webhook signature using STRIPE_WEBHOOK_SECRET
    - Returns 200 OK for all valid signatures
    - Returns 401 for invalid signatures

    Note: Read raw body for signature verification
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing stripe-signature header"
        )
    
    # Verify webhook signature
    if not StripeService.verify_webhook_signature(payload, sig_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse event
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Process webhook event
    result = RendezVousService.handle_stripe_webhook(event, db)
    
    # Return 200 OK to acknowledge receipt
    return {"status": "received", "result": result}


# ===============================
# PAYMENT STATUS
# ===============================

@router.get("/{rdv_id}/status", response_model=rendezvous_schemas.PaymentIntentStatusResponse)
def get_payment_status(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "patient", "doctor"])),
):
    """
    Get the payment status of an appointment.
    
    Returns:
    - payment_intent_id: Stripe payment ID
    - status: Current payment status from Stripe
    - amount: Amount in cents
    - currency: Currency code
    
    Access control:
    - Patients: Own appointments only
    - Doctors: Own appointments only
    - Admins: Any appointment
    """
    appointment = db.query(models.RendezVous).filter(
        models.RendezVous.id == rdv_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Access control
    if current_user.role == "patient":
        patient = _get_or_create_patient_profile(db, current_user.id)
        if appointment.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    elif current_user.role == "doctor":
        doctor = db.query(models.Doctor).filter(
            models.Doctor.user_id == current_user.id
        ).first()
        if not doctor or appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Get payment status from Stripe if we have a payment intent ID
    if appointment.payment_intent_id:
        return StripeService.get_payment_intent_status(appointment.payment_intent_id)
    
    # No payment intent created yet
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No payment intent created for this appointment yet"
    )


# ===============================
# MANUAL PAYMENT CONFIRMATION (Admin only)
# ===============================

@router.post("/{rdv_id}/manual-confirm", response_model=rendezvous_schemas.RendezVousResponse)
def manual_confirm_payment(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin"])),
):
    """
    Manually confirm payment for an appointment (admin only).
    
    Used for:
    - Manual payment verification
    - Off-platform payment processing
    - Payment corrections
    
    Updates appointment status to 'confirmed' and payment_status to 'paid'.
    """
    appointment = db.query(models.RendezVous).filter(
        models.RendezVous.id == rdv_id
    ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Confirm payment through service
    confirmed_appointment = RendezVousService.confirm_appointment_after_payment(rdv_id, db)
    
    return confirmed_appointment


# ===============================
# PAYMENT LISTING
# ===============================

@router.get("/", response_model=List[rendezvous_schemas.PaymentResponse])
def list_payments(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """List payment records scoped by user role.

    - Admins see all payments
    - Doctors see payments for their own appointments
    - Patients see payments for their own appointments
    """
    appointments = RendezVousService.list_payments_for_user(current_user, db)
    return appointments


@router.post("/charge")
def charge_patient(current_user=Depends(require_roles(["admin"]))):
    """Charge patient endpoint (placeholder - use create-intent instead)"""
    return {"message": "Use /payments/create-intent/{rdv_id} for payment processing"}
