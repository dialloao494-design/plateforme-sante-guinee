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
    def _get_frontend_url() -> str:
        """Return the frontend base URL normalized for HTTPS Stripe redirects."""
        frontend_url = (os.getenv("FRONTEND_URL") or "").strip().rstrip("/")

        if not frontend_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FRONTEND_URL environment variable is not configured"
            )

        if frontend_url.startswith("http://"):
            frontend_url = frontend_url.replace("http://", "https://", 1)

        if not frontend_url.startswith("https://"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FRONTEND_URL must use HTTPS"
            )

        return frontend_url

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
            if "amount_refunded" not in columns:
                statements.append("ALTER TABLE payments ADD COLUMN amount_refunded INTEGER DEFAULT 0")
            if "refund_status" not in columns:
                statements.append("ALTER TABLE payments ADD COLUMN refund_status VARCHAR DEFAULT 'none'")
            if "settlement_channel" not in columns:
                statements.append("ALTER TABLE payments ADD COLUMN settlement_channel VARCHAR")
            if "last_stripe_event_id" not in columns:
                statements.append("ALTER TABLE payments ADD COLUMN last_stripe_event_id VARCHAR")

            if "stripe_webhook_events" not in inspector.get_table_names():
                from models.stripe_webhook_event import StripeWebhookEvent

                StripeWebhookEvent.__table__.create(bind=db.bind, checkfirst=True)

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
        settlement_channel: Optional[str] = None,
        stripe_event_id: Optional[str] = None,
        amount_refunded: int = 0,
        refund_status: str = "none",
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
                    amount_refunded=amount_refunded,
                    currency=currency,
                    status=status_value,
                    refund_status=refund_status,
                    settlement_channel=settlement_channel,
                    last_stripe_event_id=stripe_event_id,
                )
                db.add(payment)
            else:
                payment.appointment_id = appointment_id
                payment.payment_id = effective_payment_id
                payment.stripe_session_id = normalized_session_id or payment.stripe_session_id
                payment.amount = amount
                payment.currency = currency
                payment.status = status_value
                payment.amount_refunded = amount_refunded
                payment.refund_status = refund_status
                if settlement_channel:
                    payment.settlement_channel = settlement_channel
                if stripe_event_id:
                    payment.last_stripe_event_id = stripe_event_id
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
        from services.payment_settlement import PaymentSettlementService

        StripeService.validate_stripe_config()
        PaymentSettlementService.assert_checkout_allowed(db, appointment_id)
        frontend_url = StripeService._get_frontend_url()

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
                success_url=f"{frontend_url}/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_url}/cancel",
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
        from core.payment_policy import SETTLEMENT_CHANNEL_STRIPE_CHECKOUT
        from services.payment_settlement import PaymentSettlementService
        from services.stripe_verification import StripePaymentVerifier

        proof = StripePaymentVerifier.verify_checkout_session(
            session_id,
            expected_patient_user_id=expected_patient_user_id,
            db=db,
        )

        return PaymentSettlementService.settle_appointment(
            db,
            int(proof.appointment_id),
            channel=SETTLEMENT_CHANNEL_STRIPE_CHECKOUT,
            stripe_payment_intent_id=proof.payment_intent_id,
            stripe_session_id=session_id,
            amount_cents=proof.net_amount_cents,
            currency=proof.currency,
        )

    @staticmethod
    def parse_webhook_event(payload: bytes, signature: str) -> Dict[str, Any]:
        """Verify signature and return the parsed Stripe event (never trust raw JSON alone)."""
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe webhook secret not configured",
            )

        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=webhook_secret,
            )
            if hasattr(event, "to_dict"):
                return event.to_dict()
            return dict(event)
        except stripe.error.SignatureVerificationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Webhook verification failed: {exc}",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook verification failed: {exc}",
            ) from exc

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify that a webhook request came from Stripe.

        Deprecated: prefer ``parse_webhook_event`` which returns the verified event.
        """
        StripeService.parse_webhook_event(payload, signature)
        return True

    @staticmethod
    def handle_webhook_event(
        event: Dict[str, Any],
        db: Session
    ) -> Dict[str, str]:
        """
        Handle Stripe webhook events via idempotent processor.

        Delegates to ``StripeWebhookProcessor`` for deduplication, settlement,
        refunds, and failure handling.
        """
        from services.stripe_webhook_processor import StripeWebhookProcessor

        try:
            return StripeWebhookProcessor.process(event, db)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Webhook processing error: {str(e)}"
            )

    @staticmethod
    def _handle_payment_succeeded(
        appointment: models.RendezVous,
        payment_intent: Dict[str, Any],
        db: Session,
    ) -> models.RendezVous:
        """
        Legacy entry point — delegates to centralized settlement (Stripe webhook channel).
        """
        from core.payment_policy import SETTLEMENT_CHANNEL_STRIPE_WEBHOOK
        from services.payment_settlement import PaymentSettlementService

        return PaymentSettlementService.settle_appointment(
            db,
            appointment.id,
            channel=SETTLEMENT_CHANNEL_STRIPE_WEBHOOK,
            stripe_payment_intent_id=payment_intent.get("id", appointment.payment_intent_id or ""),
            stripe_session_id=payment_intent.get("stripe_session_id"),
            amount_cents=int(payment_intent.get("amount_received") or payment_intent.get("amount") or 0),
            currency=(payment_intent.get("currency") or "eur").lower(),
        )

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
