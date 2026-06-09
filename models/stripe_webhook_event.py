"""Persisted Stripe webhook events for idempotent processing (at-least-once delivery)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    # Stripe event id (evt_...) — global idempotency key.
    stripe_event_id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False, index=True)
    appointment_id = Column(Integer, nullable=True, index=True)
    payment_intent_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="processing", index=True)
    result_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
