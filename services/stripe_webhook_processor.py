"""
Idempotent Stripe webhook processor.

Stripe delivers webhooks at-least-once. We persist every ``event.id`` before side effects
and return cached results on replay — matching Stripe's recommended idempotency pattern.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from core.payment_policy import SETTLEMENT_CHANNEL_STRIPE_WEBHOOK
from models.stripe_webhook_event import StripeWebhookEvent
from services.payment_refunds import PaymentRefundService
from services.payment_settlement import PaymentSettlementService
from services.stripe_service import StripeService

logger = logging.getLogger(__name__)

SETTLEMENT_EVENTS = frozenset(
    {
        "payment_intent.succeeded",
        "checkout.session.completed",
    }
)
REFUND_EVENTS = frozenset(
    {
        "charge.refunded",
        "refund.created",
        "refund.updated",
    }
)
FAILURE_EVENTS = frozenset(
    {
        "payment_intent.payment_failed",
        "checkout.session.expired",
    }
)


class StripeWebhookProcessor:
    @staticmethod
    def process(event: dict[str, Any], db: Session) -> dict[str, Any]:
        event_id = str(event.get("id") or "")
        event_type = str(event.get("type") or "")

        if not event_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe event missing id",
            )

        existing = (
            db.query(StripeWebhookEvent)
            .filter(StripeWebhookEvent.stripe_event_id == event_id)
            .first()
        )
        if existing and existing.status == "completed":
            cached = StripeWebhookProcessor._deserialize_result(existing.result_json)
            return {
                **cached,
                "idempotency": "replay",
                "stripe_event_id": event_id,
            }

        if not existing:
            existing = StripeWebhookEvent(
                stripe_event_id=event_id,
                event_type=event_type,
                status="processing",
            )
            db.add(existing)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raced = (
                    db.query(StripeWebhookEvent)
                    .filter(StripeWebhookEvent.stripe_event_id == event_id)
                    .first()
                )
                if raced and raced.status == "completed":
                    cached = StripeWebhookProcessor._deserialize_result(raced.result_json)
                    return {**cached, "idempotency": "replay", "stripe_event_id": event_id}
                return {
                    "status": "duplicate",
                    "idempotency": "concurrent_claim",
                    "stripe_event_id": event_id,
                }

        try:
            result = StripeWebhookProcessor._dispatch(event, db, stripe_event_id=event_id)
        except Exception as exc:
            existing.status = "failed"
            existing.result_json = json.dumps({"status": "error", "detail": str(exc)})
            existing.processed_at = datetime.utcnow()
            db.commit()
            raise

        existing.status = "completed"
        existing.event_type = event_type
        existing.appointment_id = result.get("appointment_id")
        existing.payment_intent_id = result.get("payment_intent_id")
        existing.result_json = json.dumps(result)
        existing.processed_at = datetime.utcnow()
        db.commit()

        return {**result, "idempotency": "processed", "stripe_event_id": event_id}

    @staticmethod
    def _dispatch(
        event: dict[str, Any],
        db: Session,
        *,
        stripe_event_id: str,
    ) -> dict[str, Any]:
        event_type = event.get("type")
        obj = event.get("data", {}).get("object", {})

        if event_type in SETTLEMENT_EVENTS:
            return StripeWebhookProcessor._handle_settlement(
                event_type, obj, db, stripe_event_id=stripe_event_id
            )
        if event_type in REFUND_EVENTS:
            return StripeWebhookProcessor._handle_refund(
                event_type, obj, db, stripe_event_id=stripe_event_id
            )
        if event_type in FAILURE_EVENTS:
            return StripeWebhookProcessor._handle_failure(event_type, obj, db)

        return {
            "status": "skipped",
            "reason": f"Unhandled event type: {event_type}",
            "event": event_type,
        }

    @staticmethod
    def _handle_settlement(
        event_type: str,
        obj: dict[str, Any],
        db: Session,
        *,
        stripe_event_id: str,
    ) -> dict[str, Any]:
        if event_type == "checkout.session.completed":
            appointment_id = (obj.get("metadata") or {}).get("appointment_id")
            if obj.get("payment_status") != "paid":
                return {
                    "status": "skipped",
                    "reason": "Checkout session not fully paid",
                    "event": event_type,
                }
            payment_intent_id = obj.get("payment_intent")
            if isinstance(payment_intent_id, dict):
                payment_intent_id = payment_intent_id.get("id")
            session_id = obj.get("id")
        else:
            appointment_id = (obj.get("metadata") or {}).get("appointment_id")
            payment_intent_id = obj.get("id")
            session_id = None

        if not appointment_id:
            return {"status": "skipped", "reason": "No appointment_id in metadata", "event": event_type}

        appointment = (
            db.query(models.RendezVous)
            .filter(models.RendezVous.id == int(appointment_id))
            .first()
        )
        if not appointment:
            return {
                "status": "skipped",
                "reason": f"Appointment {appointment_id} not found",
                "event": event_type,
            }

        settled = PaymentSettlementService.settle_appointment(
            db,
            appointment.id,
            channel=SETTLEMENT_CHANNEL_STRIPE_WEBHOOK,
            stripe_payment_intent_id=str(payment_intent_id or appointment.payment_intent_id or ""),
            stripe_session_id=session_id,
            stripe_event_id=stripe_event_id,
        )

        return {
            "status": "success",
            "event": event_type,
            "appointment_id": settled.id,
            "payment_intent_id": settled.payment_intent_id,
            "message": "Appointment settled via webhook",
        }

    @staticmethod
    def _handle_refund(
        event_type: str,
        obj: dict[str, Any],
        db: Session,
        *,
        stripe_event_id: str,
    ) -> dict[str, Any]:
        if event_type == "charge.refunded":
            updated = PaymentRefundService.apply_from_charge_object(
                db, obj, stripe_event_id=stripe_event_id
            )
        else:
            updated = PaymentRefundService.apply_from_refund_object(
                db, obj, stripe_event_id=stripe_event_id
            )
            if updated is None:
                return {
                    "status": "skipped",
                    "reason": "Refund event missing charge reference",
                    "event": event_type,
                }

        return {
            "status": "success",
            "event": event_type,
            "appointment_id": updated.id,
            "payment_intent_id": updated.payment_intent_id,
            "payment_status": updated.payment_status,
            "message": "Refund applied",
        }

    @staticmethod
    def _handle_failure(
        event_type: str,
        obj: dict[str, Any],
        db: Session,
    ) -> dict[str, Any]:
        if event_type == "checkout.session.expired":
            appointment_id = (obj.get("metadata") or {}).get("appointment_id")
            payment_payload = {
                "id": None,
                "amount": obj.get("amount_total") or 0,
                "currency": (obj.get("currency") or "eur").lower(),
                "stripe_session_id": obj.get("id"),
                "status": "cancelled",
            }
        else:
            appointment_id = (obj.get("metadata") or {}).get("appointment_id")
            payment_payload = obj

        if not appointment_id:
            return {"status": "skipped", "reason": "No appointment_id in metadata", "event": event_type}

        appointment = (
            db.query(models.RendezVous)
            .filter(models.RendezVous.id == int(appointment_id))
            .first()
        )
        if not appointment:
            return {
                "status": "skipped",
                "reason": f"Appointment {appointment_id} not found",
                "event": event_type,
            }

        updated = StripeService._handle_payment_failed(appointment, payment_payload, db)
        return {
            "status": "success",
            "event": event_type,
            "appointment_id": updated.id,
            "message": "Payment failure recorded",
        }

    @staticmethod
    def _deserialize_result(raw: Optional[str]) -> dict[str, Any]:
        if not raw:
            return {"status": "unknown"}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "unknown", "raw": raw}
