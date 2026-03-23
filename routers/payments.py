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
from typing import Optional
import json

from database import get_db
import models
from security import get_current_admin, get_current_doctor, get_current_patient, require_roles
from services.rendezvous_service import RendezVousService
from services.stripe_service import StripeService
from schemas import rendezvous as rendezvous_schemas

router = APIRouter(prefix="/payments", tags=["Payments"])


# ===============================
# PAYMENT INTENT CREATION
# ===============================

@router.post("/create-intent/{rdv_id}", response_model=rendezvous_schemas.PaymentIntentResponse)
def create_payment_intent(
    rdv_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_patient),
):
    """
    Create a Stripe payment intent for an appointment.
    
    - Creates a payment intent with the appointment price
    - Stores payment_intent_id in the appointment record
    - Does NOT confirm the appointment yet
    - Patient must own the appointment
    
    Returns:
    - client_secret: For frontend payment processing
    - payment_intent_id: Stripe ID
    - amount: Price in cents
    - status: Payment intent status
    """
    # Get patient profile
    patient = db.query(models.Patient).filter(
        models.Patient.user_id == current_user.id
    ).first()
    
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    # Verify patient owns this appointment
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
    
    # Create payment intent via service
    payment_intent = RendezVousService.create_payment_intent(rdv_id, db)
    
    return payment_intent


# ===============================
# STRIPE WEBHOOK
# ===============================

@router.post("/webhook")
def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle Stripe webhook events.
    
    Stripe sends webhook notifications for payment events:
    - payment_intent.succeeded: Payment successful → confirm appointment
    - payment_intent.payment_failed: Payment failed → mark as unpaid
    
    Security:
    - Verifies webhook signature using STRIPE_WEBHOOK_SECRET
    - Returns 200 OK for all valid signatures
    - Returns 401 for invalid signatures
    
    Note: Read raw body for signature verification
    """
    payload = request.body
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
        patient = db.query(models.Patient).filter(
            models.Patient.user_id == current_user.id
        ).first()
        if not patient or appointment.patient_id != patient.id:
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
# LEGACY ENDPOINTS
# ===============================

@router.get("/")
def list_payments(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    """List payments (placeholder - use appointment endpoints instead)"""
    return {"message": "Use appointment endpoints for payment information"}


@router.post("/charge")
def charge_patient(current_user=Depends(require_roles(["admin"]))):
    """Charge patient endpoint (placeholder - use create-intent instead)"""
    return {"message": "Use /payments/create-intent/{rdv_id} for payment processing"}
