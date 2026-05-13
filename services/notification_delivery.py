"""Transactional notification delivery — SMS / email / push hooks (env-driven)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)


def record_in_app_notification(
    db: Session,
    *,
    user_id: int,
    subject: str,
    body: str,
    channel: str = "in_app",
    meta: dict[str, Any] | None = None,
) -> models.NotificationEvent | None:
    """Persist a notification row for the notification center and audit."""
    try:
        row = models.NotificationEvent(
            user_id=user_id,
            channel=channel,
            subject=subject[:255],
            body=body,
            meta=json.dumps(meta)[:1024] if meta else None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as exc:
        logger.warning("Could not record notification: %s", exc)
        db.rollback()
        return None


def describe_notification_channels() -> dict:
    """Capability flags merged with env (SMS_EMAIL_ENABLED, PUSH_VAPID_PUBLIC_KEY, etc.)."""
    sms_ready = bool(os.getenv("SMS_PROVIDER_URL") or os.getenv("TWILIO_ACCOUNT_SID"))
    email_ready = bool(os.getenv("SMTP_HOST") or os.getenv("RESEND_API_KEY"))
    push_ready = bool(os.getenv("VAPID_PUBLIC_KEY") or os.getenv("WEB_PUSH_PUBLIC_KEY"))
    return {
        "enabled": sms_ready or email_ready or push_ready,
        "channels": [
            {
                "id": "sms",
                "label": "SMS (Orange, MTN)",
                "status": "live" if sms_ready else "planned",
                "use_cases": ["rappel_rdv", "teleconsultation", "paiement_confirme"],
            },
            {
                "id": "email",
                "label": "Email transactionnel",
                "status": "live" if email_ready else "planned",
                "use_cases": ["confirmation", "recu_paiement"],
            },
            {
                "id": "push",
                "label": "Notifications navigateur (Web Push)",
                "status": "live" if push_ready else "planned",
                "use_cases": ["message_securise", "rappel_rdv"],
            },
        ],
    }
