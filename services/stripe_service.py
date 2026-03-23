"""
Stripe Payment Service Layer

Handles all Stripe payment operations:
- Creating payment intents
- Verifying webhook signatures
- Processing webhook events
- Managing payment status
"""

import os
import stripe
import hmac
import hashlib
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

import models
from services.rendezvous_service import RendezVousService


class StripeService:
    """Service for managing Stripe payment operations"""

    # Initialize Stripe with API key from environment
    STRIPE_API_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not STRIPE_API_KEY:
        raise ValueError("STRIPE_SECRET_KEY environment variable not set")

    stripe.api_key = STRIPE_API_KEY

    @staticmethod
    def validate_stripe_config():
        """Validate that Stripe is properly configured"""
        if not StripeService.STRIPE_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe API key not configured"
            )

    @staticmethod
    def create_payment_intent(
        appointment_id: int,
        appointment_price: float,
        patient_email: str,
        patient_name: str,
        doctor_name: str,
        appointment_date: str,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe payment intent for an appointment.

        Args:
            appointment_id: The appointment ID
            appointment_price: Price in local currency (will be converted to cents for Stripe)
            patient_email: Patient email for receipt
            patient_name: Patient name
            doctor_name: Doctor name for description
            appointment_date: Appointment date/time as string
            db: Database session (optional, for updating appointment)

        Returns:
            Dict with client_secret and payment intent details

        Raises:
            HTTPException if payment intent creation fails
        """
        StripeService.validate_stripe_config()

        try:
            # Convert price to cents (Stripe requires amounts in smallest currency unit)
            amount_cents = int(appointment_price * 100)

            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="gnf",  # Guinea Francs - adjust if needed
                payment_method_types=["card"],
                description=f"Appointment with {doctor_name} on {appointment_date}",
                receipt_email=patient_email,
                metadata={
                    "appointment_id": str(appointment_id),
                    "patient_name": patient_name,
                    "doctor_name": doctor_name,
                    "appointment_date": appointment_date,
                },
            )

            # Update appointment with payment intent ID if db session provided
            if db:
                appointment = db.query(models.RendezVous).filter(
                    models.RendezVous.id == appointment_id
                ).first()
                if appointment:
                    appointment.payment_intent_id = payment_intent.id
                    appointment.updated_at = datetime.utcnow()
                    db.commit()
                    db.refresh(appointment)

            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": payment_intent.status,
            }

        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment intent: {str(e)}"
            )

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify that a webhook request came from Stripe.

        Args:
            payload: Raw request body
            signature: Stripe signature header value

        Returns:
            True if signature is valid, False otherwise

        Raises:
            HTTPException if webhook secret not configured
        """
        if not StripeService.STRIPE_WEBHOOK_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe webhook secret not configured"
            )

        try:
            # Verify signature
            expected_sig = hmac.new(
                StripeService.STRIPE_WEBHOOK_SECRET.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(expected_sig, signature)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Webhook verification failed: {str(e)}"
            )

    @staticmethod
    def handle_webhook_event(
        event: Dict[str, Any],
        db: Session
    ) -> Dict[str, str]:
        """
        Handle Stripe webhook events.

        Supported events:
        - payment_intent.succeeded: Payment successful → confirm appointment
        - payment_intent.payment_failed: Payment failed → mark as unpaid

        Args:
            event: Parsed webhook event from Stripe
            db: Database session

        Returns:
            Dict with event handling result

        Raises:
            HTTPException on processing errors
        """
        event_type = event.get("type")
        payment_intent = event.get("data", {}).get("object", {})
        appointment_id = payment_intent.get("metadata", {}).get("appointment_id")

        try:
            # Validate appointment exists
            if not appointment_id:
                return {
                    "status": "skipped",
                    "reason": "No appointment_id in metadata"
                }

            appointment = db.query(models.RendezVous).filter(
                models.RendezVous.id == int(appointment_id)
            ).first()

            if not appointment:
                return {
                    "status": "skipped",
                    "reason": f"Appointment {appointment_id} not found"
                }

            # Handle payment success
            if event_type == "payment_intent.succeeded":
                appointment = StripeService._handle_payment_succeeded(
                    appointment, payment_intent, db
                )
                return {
                    "status": "success",
                    "event": event_type,
                    "appointment_id": str(appointment.id),
                    "message": "Appointment confirmed after payment"
                }

            # Handle payment failure
            elif event_type == "payment_intent.payment_failed":
                appointment = StripeService._handle_payment_failed(
                    appointment, payment_intent, db
                )
                return {
                    "status": "success",
                    "event": event_type,
                    "appointment_id": str(appointment.id),
                    "message": "Appointment marked as unpaid"
                }

            else:
                return {
                    "status": "skipped",
                    "reason": f"Unhandled event type: {event_type}"
                }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook processing error: {str(e)}"
            )

    @staticmethod
    def _handle_payment_succeeded(
        appointment: models.RendezVous,
        payment_intent: Dict[str, Any],
        db: Session
    ) -> models.RendezVous:
        """
        Handle successful payment.
        
        Confirms appointment and marks as paid.
        """
        # Only process if appointment is still pending
        if appointment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm payment for appointment with status {appointment.status}"
            )

        appointment.status = "confirmed"
        appointment.payment_status = "paid"
        appointment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(appointment)

        return appointment

    @staticmethod
    def _handle_payment_failed(
        appointment: models.RendezVous,
        payment_intent: Dict[str, Any],
        db: Session
    ) -> models.RendezVous:
        """
        Handle failed payment.
        
        Marks appointment as unpaid, keeps status as pending.
        """
        # Mark payment as unpaid but keep appointment pending
        appointment.payment_status = "unpaid"
        appointment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(appointment)

        return appointment

    @staticmethod
    def get_payment_intent_status(payment_intent_id: str) -> Dict[str, Any]:
        """
        Get the current status of a payment intent from Stripe.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Payment intent details

        Raises:
            HTTPException if payment intent not found or API error
        """
        StripeService.validate_stripe_config()

        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "payment_intent_id": payment_intent.id,
                "status": payment_intent.status,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "client_secret": payment_intent.client_secret,
            }
        except stripe.error.InvalidRequestError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment intent not found"
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to retrieve payment intent: {str(e)}"
            )

    @staticmethod
    def cancel_payment_intent(payment_intent_id: str) -> Dict[str, str]:
        """
        Cancel a Stripe payment intent.

        Args:
            payment_intent_id: Stripe payment intent ID

        Returns:
            Cancellation status

        Raises:
            HTTPException on error
        """
        StripeService.validate_stripe_config()

        try:
            payment_intent = stripe.PaymentIntent.cancel(payment_intent_id)
            return {
                "status": "cancelled",
                "payment_intent_id": payment_intent.id,
            }
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel payment intent: {str(e)}"
            )
