"""Privacy-conscious, best-effort persistence for authentication outcomes."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fastapi import Request
from sqlalchemy.orm import Session

from models.authentication_event import AuthenticationEvent
from models.user import User
from services.auth_session_service import client_meta

logger = logging.getLogger(__name__)


def email_fingerprint(email: str) -> str:
    normalized = (email or "").strip().lower().encode("utf-8")
    key = os.getenv("SECRET_KEY", "").encode("utf-8")
    return hmac.new(key, normalized, hashlib.sha256).hexdigest()


def record_authentication_event(
    db: Session,
    *,
    email: str,
    succeeded: bool,
    reason: str,
    request: Request | None = None,
    user: User | None = None,
) -> None:
    """Persist one outcome without retaining submitted credentials or raw email."""
    try:
        user_agent, ip_address = client_meta(request) if request is not None else (None, None)
        request_id = request.headers.get("x-request-id") if request is not None else None
        db.add(
            AuthenticationEvent(
                user_id=getattr(user, "id", None),
                clinic_id=getattr(user, "clinic_id", None),
                event_type="login",
                succeeded=succeeded,
                reason=reason[:64],
                email_fingerprint=email_fingerprint(email),
                ip_address=ip_address,
                user_agent=(user_agent[:512] if user_agent else None),
                request_id=(request_id[:128] if request_id else None),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not persist authentication event reason=%s", reason)
