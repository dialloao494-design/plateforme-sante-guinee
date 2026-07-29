"""Shared-secret token for unauthenticated reminder response endpoints."""

from __future__ import annotations

import hashlib
import hmac
import os


def _respond_secret() -> str:
    return (os.getenv("REMINDER_RESPOND_TOKEN") or "").strip()


def reminder_respond_token_configured() -> bool:
    return bool(_respond_secret())


def expected_reminder_respond_token(appointment_id: int) -> str:
    secret = _respond_secret()
    if not secret:
        return ""
    digest = hmac.new(
        secret.encode("utf-8"),
        str(appointment_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:32]


def verify_reminder_respond_token(appointment_id: int, token: str | None) -> bool:
    secret = _respond_secret()
    # Fail closed — never accept unsigned reminder responses when secret unset.
    if not secret:
        return False
    if not token:
        return False
    expected = expected_reminder_respond_token(appointment_id)
    return hmac.compare_digest(expected, token.strip())
