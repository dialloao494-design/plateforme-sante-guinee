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
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from dotenv import load_dotenv

import models


load_dotenv()


class StripeService:
    """Service for managing Stripe payment operations"""

    @staticmethod
    def _ensure_payment_schema(db: Session) -> None:
        """Best-effort schema patch for existing local DBs without migrations."""
        try:
            inspector = inspect(db.bind)
            if "payments" not in inspector.get_table_names():
                return

            columns = {col["name"] for col in inspector.get_columns("payments")}
            statements = []

            if "stripe_session_id" not in columns:
                statements.append("ALTER TABLE payments ADD COLUMN stripe_session_id VARCHAR")
            if "currency" not in columns:
                statements.append("ALTER TABLE payments ADD COLUMN currency VARCHAR")

            for stmt in statements:
                db.execute(text(stmt))

            if statements:
                db.commit()
        except Exception:
            db.rollback()

    @staticmethod
    def _upsert_payment_record(
        db: Session,
        appointment_id: int,
        payment_id: Optional[str],
        stripe_session_id: Optional[str],
        amount: int,
        currency: str,
        status_value: str,
    ) -> models.Payment:
        """Create or update a payment record linked to an appointment."""
        StripeService._ensure_payment_schema(db)

        normalized_payment_id = payment_id.strip() if isinstance(payment_id, str) and payment_id.strip() else None
        normalized_session_id = stripe_session_id.strip() if isinstance(stripe_session_id, str) and stripe_session_id.strip() else None

        # Use checkout session ID as fallback identifier when payment_intent is not yet attached.
        effective_payment_id = normalized_payment_id or normalized_session_id

        if not effective_payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe payment/session ID; payment record was not created"
            )

        payment = None
        if effective_payment_id:
            payment = db.query(models.Payment).filter(
                models.Payment.payment_id == effective_payment_id
            ).first()

        if not payment and normalized_session_id:
            payment = db.query(models.Payment).filter(
                models.Payment.stripe_session_id == normalized_session_id
            ).first()

        try:
            if not payment:
                payment = models.Payment(
                    appointment_id=appointment_id,
                    payment_id=effective_payment_id,
                    stripe_session_id=normalized_session_id,
                    amount=amount,
                    currency=currency,
                    status=status_value,
                )
                db.add(payment)
            else:
                payment.appointment_id = appointment_id
                payment.payment_id = effective_payment_id
                payment.stripe_session_id = normalized_session_id or payment.stripe_session_id
                payment.amount = amount
                payment.currency = currency
                payment.status = status_value
                payment.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(payment)
            return payment
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to persist payment: invalid or missing Stripe payment identifier"
            )

    @staticmethod
    def configure_stripe() -> str | None:
        """Apply the current API key to the Stripe SDK and return it."""
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        return stripe.api_key

    @staticmethod
    def validate_stripe_config():
        """Validate that Stripe is properly configured"""
        if not StripeService.configure_stripe():
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
        amount_cents = int(appointment_price * 100)
        StripeService.validate_stripe_config()

        try:
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
                    appointment.payment_status = "unpaid"
                    appointment.updated_at = datetime.utcnow()
                    db.commit()
                    db.refresh(appointment)

                    # Persist payment record in DB and link to appointment.
                    StripeService._upsert_payment_record(
                        db=db,
                        appointment_id=appointment.id,
                        payment_id=payment_intent.id,
                        stripe_session_id=None,
                        amount=payment_intent.amount,
                        currency=(payment_intent.currency or "eur").lower(),
                        status_value="pending",
                    )

            return {
                "client_secret": payment_intent.client_secret,
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": payment_intent.status,
            }

        except stripe.error.AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Stripe authentication failed: {str(e)}"
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create payment intent: {str(e)}"
            )

    @staticmethod
    def create_checkout_session(
        appointment_id: int,
        appointment_price: float,
        patient_email: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Create Stripe Checkout session and persist pending payment linkage."""
        StripeService.validate_stripe_config()

        # Default to 50.00 EUR when appointment has no price configured.
        unit_amount = int(appointment_price * 100) if appointment_price and appointment_price > 0 else 5000

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "eur",
                            "product_data": {
                                "name": "Consultation medicale",
                            },
                            "unit_amount": unit_amount,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                customer_email=patient_email,
                metadata={"appointment_id": str(appointment_id)},
                success_url="http://localhost:5173/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="http://localhost:5173/cancel",
            )

            appointment = db.query(models.RendezVous).filter(
                models.RendezVous.id == appointment_id
            ).first()
            if appointment:
                payment_intent_ref = session.get("payment_intent")
                if payment_intent_ref:
                    appointment.payment_intent_id = payment_intent_ref
                appointment.payment_status = "unpaid"
                appointment.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(appointment)

                StripeService._upsert_payment_record(
                    db=db,
                    appointment_id=appointment.id,
                    payment_id=payment_intent_ref if isinstance(payment_intent_ref, str) and payment_intent_ref else session.id,
                    stripe_session_id=session.id,
                    amount=unit_amount,
                    currency="eur",
                    status_value="pending",
                )

            return {
                "checkout_url": session.url,
                "session_id": session.id,
                "status": session.status,
            }
        except stripe.error.AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Stripe authentication failed: {str(e)}"
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create checkout session: {str(e)}"
            )

    @staticmethod
    def confirm_checkout_session(
        session_id: str,
        db: Session,
        expected_patient_user_id: Optional[int] = None,
    ) -> models.RendezVous:
        """Validate Stripe Checkout session and confirm appointment only on successful payment."""
        StripeService.validate_stripe_config()

        try:
            session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        except stripe.error.InvalidRequestError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checkout session not found"
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to verify checkout session: {str(e)}"
            )

        appointment_id = (session.get("metadata") or {}).get("appointment_id")
        if not appointment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing appointment_id in checkout session metadata"
            )

        appointment = db.query(models.RendezVous).filter(
            models.RendezVous.id == int(appointment_id)
        ).first()
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )

        if expected_patient_user_id is not None:
            patient = db.query(models.Patient).filter(
                models.Patient.id == appointment.patient_id
            ).first()
            if not patient or patient.user_id != expected_patient_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )

        if session.get("payment_status") != "paid":
            StripeService._upsert_payment_record(
                db=db,
                appointment_id=appointment.id,
                payment_id=None,
                stripe_session_id=session_id,
                amount=session.get("amount_total") or 0,
                currency=(session.get("currency") or "eur").lower(),
                status_value="failed" if session.get("status") == "expired" else "cancelled",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment was not successful or was cancelled on Stripe"
            )

        payment_intent_obj: Optional[Dict[str, Any]] = session.get("payment_intent")
        payment_intent_id = ""
        amount_paid = session.get("amount_total") or 0

        if isinstance(payment_intent_obj, dict):
            payment_intent_id = payment_intent_obj.get("id") or ""
            amount_paid = payment_intent_obj.get("amount_received") or amount_paid
        elif isinstance(payment_intent_obj, str):
            payment_intent_id = payment_intent_obj

        if not payment_intent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe payment intent ID after checkout"
            )

        appointment.payment_intent_id = payment_intent_id
        confirmed = StripeService._handle_payment_succeeded(
            appointment=appointment,
            payment_intent={
                "id": payment_intent_id,
                "amount_received": amount_paid,
                "currency": (session.get("currency") or "eur").lower(),
                "stripe_session_id": session_id,
            },
            db=db,
        )

        return confirmed

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
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe webhook secret not configured"
            )

        try:
            stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=webhook_secret,
            )
            return True

        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Webhook verification failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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
        - payment_intent.payment_failed: Payment failed → mark as failed

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

        # Stripe Checkout emits checkout.session.completed with metadata.
        if event_type in {"checkout.session.completed", "checkout.session.expired"}:
            checkout_session = payment_intent
            appointment_id = (checkout_session.get("metadata") or {}).get("appointment_id")
        else:
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

            elif event_type == "checkout.session.completed":
                checkout_payment_intent = checkout_session.get("payment_intent")
                if checkout_session.get("payment_status") != "paid":
                    return {
                        "status": "skipped",
                        "reason": "Checkout session not fully paid"
                    }

                payment_id = checkout_payment_intent if isinstance(checkout_payment_intent, str) else ""
                appointment.payment_intent_id = payment_id or appointment.payment_intent_id
                appointment = StripeService._handle_payment_succeeded(
                    appointment,
                    {
                        "id": payment_id or appointment.payment_intent_id,
                        "amount_received": checkout_session.get("amount_total") or 0,
                        "currency": (checkout_session.get("currency") or "eur").lower(),
                        "stripe_session_id": checkout_session.get("id"),
                    },
                    db,
                )
                return {
                    "status": "success",
                    "event": event_type,
                    "appointment_id": str(appointment.id),
                    "message": "Appointment confirmed after checkout completion"
                }

            elif event_type == "checkout.session.expired":
                appointment = StripeService._handle_payment_failed(
                    appointment,
                    {
                        "id": appointment.payment_intent_id,
                        "amount": checkout_session.get("amount_total") or 0,
                        "currency": (checkout_session.get("currency") or "eur").lower(),
                        "stripe_session_id": checkout_session.get("id"),
                        "status": "cancelled",
                    },
                    db,
                )
                return {
                    "status": "success",
                    "event": event_type,
                    "appointment_id": str(appointment.id),
                    "message": "Checkout session expired; appointment remains pending"
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
                    "message": "Appointment marked as payment failed"
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
        # Only process if appointment is still pending/paid-in-progress.
        if appointment.status not in {"pending", "paid"}:
            if appointment.status == "confirmed" and appointment.payment_status == "paid":
                return appointment
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm payment for appointment with status {appointment.status}"
            )

        appointment.status = "paid"
        appointment.payment_status = "paid"
        appointment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(appointment)

        appointment.status = "confirmed"
        appointment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(appointment)

        StripeService._upsert_payment_record(
            db=db,
            appointment_id=appointment.id,
            payment_id=payment_intent.get("id", appointment.payment_intent_id or ""),
            stripe_session_id=payment_intent.get("stripe_session_id"),
            amount=payment_intent.get("amount_received") or payment_intent.get("amount") or 0,
            currency=(payment_intent.get("currency") or "eur").lower(),
            status_value="paid",
        )

        return appointment

    @staticmethod
    def _handle_payment_failed(
        appointment: models.RendezVous,
        payment_intent: Dict[str, Any],
        db: Session
    ) -> models.RendezVous:
        """
        Handle failed payment.

        Marks appointment as unpaid and keeps appointment pending.
        """
        appointment.payment_status = "unpaid"
        appointment.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(appointment)

        StripeService._upsert_payment_record(
            db=db,
            appointment_id=appointment.id,
            payment_id=payment_intent.get("id", appointment.payment_intent_id or ""),
            stripe_session_id=payment_intent.get("stripe_session_id"),
            amount=payment_intent.get("amount") or 0,
            currency=(payment_intent.get("currency") or "eur").lower(),
            status_value=payment_intent.get("status") or "failed",
        )

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
