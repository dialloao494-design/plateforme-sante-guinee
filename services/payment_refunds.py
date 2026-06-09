"""Refund handling for Stripe charge.refunded / refund.* webhook events."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)

REFUND_STATUS_NONE = "none"
REFUND_STATUS_PARTIAL = "partial"
REFUND_STATUS_FULL = "full"


class PaymentRefundService:
    """Apply full or partial refunds to appointments and payment ledger rows."""

    @staticmethod
    def apply_refund(
        db: Session,
        *,
        payment_intent_id: str,
        amount_refunded_cents: int,
        amount_total_cents: int,
        currency: str = "eur",
        stripe_event_id: Optional[str] = None,
    ) -> models.RendezVous:
        if not payment_intent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund requires payment_intent_id",
            )

        appointment = (
            db.query(models.RendezVous)
            .filter(models.RendezVous.payment_intent_id == payment_intent_id)
            .with_for_update()
            .first()
        )
        if not appointment:
            appointment = PaymentRefundService._find_appointment_by_payment_record(
                db, payment_intent_id
            )
            if appointment:
                db.query(models.RendezVous).filter(
                    models.RendezVous.id == appointment.id
                ).with_for_update().first()

        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No appointment linked to payment_intent {payment_intent_id}",
            )

        locked = (
            db.query(models.RendezVous)
            .filter(models.RendezVous.id == appointment.id)
            .with_for_update()
            .first()
        )
        if not locked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

        amount_refunded_cents = max(0, int(amount_refunded_cents))
        amount_total_cents = max(amount_refunded_cents, int(amount_total_cents or 0))

        if amount_refunded_cents <= 0:
            return locked

        is_full = amount_total_cents > 0 and amount_refunded_cents >= amount_total_cents
        refund_status = REFUND_STATUS_FULL if is_full else REFUND_STATUS_PARTIAL
        new_payment_status = "refunded" if is_full else "partially_refunded"

        payment = (
            db.query(models.Payment)
            .filter(
                models.Payment.appointment_id == locked.id,
                models.Payment.payment_id == payment_intent_id,
            )
            .first()
        )
        if not payment:
            payment = (
                db.query(models.Payment)
                .filter(models.Payment.appointment_id == locked.id)
                .order_by(models.Payment.created_at.desc())
                .first()
            )

        if payment:
            payment.amount_refunded = amount_refunded_cents
            payment.refund_status = refund_status
            payment.status = "refunded" if is_full else "partially_refunded"
            payment.updated_at = datetime.utcnow()
            if stripe_event_id:
                payment.last_stripe_event_id = stripe_event_id

        locked.payment_status = new_payment_status
        locked.updated_at = datetime.utcnow()
        locked.meeting_link = None

        # Full refund before consultation completion → revert booking to pending/unpaid.
        if is_full and locked.status not in {"completed", "cancelled"}:
            locked.status = "pending"

        db.commit()
        db.refresh(locked)

        logger.info(
            "Refund applied appointment_id=%s payment_intent=%s refunded=%s total=%s full=%s event=%s",
            locked.id,
            payment_intent_id,
            amount_refunded_cents,
            amount_total_cents,
            is_full,
            stripe_event_id,
        )
        return locked

    @staticmethod
    def apply_from_charge_object(
        db: Session,
        charge: dict[str, Any],
        *,
        stripe_event_id: Optional[str] = None,
    ) -> models.RendezVous:
        payment_intent_id = charge.get("payment_intent") or ""
        if isinstance(payment_intent_id, dict):
            payment_intent_id = payment_intent_id.get("id") or ""

        amount_refunded = int(charge.get("amount_refunded") or 0)
        amount_total = int(charge.get("amount") or 0)
        currency = str(charge.get("currency") or "eur").lower()

        return PaymentRefundService.apply_refund(
            db,
            payment_intent_id=str(payment_intent_id),
            amount_refunded_cents=amount_refunded,
            amount_total_cents=amount_total,
            currency=currency,
            stripe_event_id=stripe_event_id,
        )

    @staticmethod
    def apply_from_refund_object(
        db: Session,
        refund: dict[str, Any],
        *,
        stripe_event_id: Optional[str] = None,
    ) -> Optional[models.RendezVous]:
        """Handle refund.created / refund.updated — requires charge expansion or PI lookup."""
        import stripe

        charge_id = refund.get("charge")
        if not charge_id:
            return None

        StripeService.validate_stripe_config()
        try:
            charge = stripe.Charge.retrieve(charge_id)
            charge_data = charge.to_dict() if hasattr(charge, "to_dict") else dict(charge)
        except stripe.error.StripeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to retrieve charge for refund: {exc}",
            ) from exc

        return PaymentRefundService.apply_from_charge_object(
            db, charge_data, stripe_event_id=stripe_event_id
        )

    @staticmethod
    def _find_appointment_by_payment_record(
        db: Session, payment_intent_id: str
    ) -> Optional[models.RendezVous]:
        payment = (
            db.query(models.Payment)
            .filter(models.Payment.payment_id == payment_intent_id)
            .first()
        )
        if not payment:
            return None
        return db.query(models.RendezVous).filter(models.RendezVous.id == payment.appointment_id).first()
