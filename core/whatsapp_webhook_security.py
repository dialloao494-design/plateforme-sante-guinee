"""WhatsApp Cloud API webhook authenticity — fail closed without App Secret."""

from __future__ import annotations

import hashlib
import hmac
import os


class WhatsAppWebhookAuthError(Exception):
    """Raised when a webhook request fails authenticity checks."""


def _app_secret() -> str:
    return (os.getenv("WHATSAPP_APP_SECRET") or "").strip()


def whatsapp_app_secret_configured() -> bool:
    return bool(_app_secret())


def verify_whatsapp_signature(*, raw_body: bytes, signature_header: str | None) -> None:
    """
    Verify Meta X-Hub-Signature-256 (HMAC-SHA256 of raw body with App Secret).

    Fail closed when WHATSAPP_APP_SECRET is unset — unauthenticated mutation of
    appointment state via the webhook must never be possible.
    """
    secret = _app_secret()
    if not secret:
        raise WhatsAppWebhookAuthError("WHATSAPP_APP_SECRET is not configured")

    if not signature_header or not str(signature_header).strip():
        raise WhatsAppWebhookAuthError("missing X-Hub-Signature-256")

    header = str(signature_header).strip()
    if header.lower().startswith("sha256="):
        provided = header.split("=", 1)[1].strip()
    else:
        provided = header

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise WhatsAppWebhookAuthError("invalid webhook signature")
