"""Orange Money / MTN MoMo webhook authenticity — fail closed in production."""

from __future__ import annotations

import hashlib
import hmac
import os

from core.payment_policy import validate_stub_token
from core.settings import get_settings


class MobileMoneyWebhookAuthError(Exception):
    """Raised when a mobile-money webhook fails authenticity checks."""


def _env_flag(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _secret_for_provider(provider: str) -> str:
    if provider == "orange_gn":
        return (
            (os.getenv("ORANGE_MONEY_WEBHOOK_SECRET") or "").strip()
            or (os.getenv("ORANGE_MONEY_API_KEY") or "").strip()
        )
    if provider == "mtn_gn":
        return (
            (os.getenv("MTN_MOMO_WEBHOOK_SECRET") or "").strip()
            or (os.getenv("MTN_MOMO_API_KEY") or "").strip()
        )
    return ""


def provider_live(provider: str) -> bool:
    if provider == "orange_gn":
        return _env_flag("ORANGE_MONEY_LIVE")
    if provider == "mtn_gn":
        return _env_flag("MTN_MOMO_LIVE")
    return False


def webhook_secret_configured(provider: str) -> bool:
    return bool(_secret_for_provider(provider))


def _normalize_signature(signature_header: str | None) -> str:
    if not signature_header or not str(signature_header).strip():
        return ""
    header = str(signature_header).strip()
    if header.lower().startswith("sha256="):
        return header.split("=", 1)[1].strip()
    return header


def verify_mobile_money_signature(
    *,
    provider: str,
    raw_body: bytes,
    signature_header: str | None,
    stub_token_header: str | None = None,
) -> None:
    """
    Verify HMAC-SHA256 webhook signature for Orange Money / MTN MoMo callbacks.

    Fail closed in production (and whenever the provider *_LIVE flag is set) when
    the webhook secret is unset. Unsigned callbacks must never mutate payment state.
  """
    settings = get_settings()
    live = provider_live(provider)
    secret = _secret_for_provider(provider)

    if settings.is_production or live:
        if not secret:
            raise MobileMoneyWebhookAuthError(
                f"Webhook secret is not configured for provider {provider}"
            )
        provided = _normalize_signature(signature_header)
        if not provided:
            raise MobileMoneyWebhookAuthError("missing webhook signature header")
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, provided):
            raise MobileMoneyWebhookAuthError("invalid webhook signature")
        return

    # Non-production stub path: signed webhooks still preferred; dev stub token allowed.
    if secret:
        provided = _normalize_signature(signature_header)
        if provided:
            expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
            if hmac.compare_digest(expected, provided):
                return
            raise MobileMoneyWebhookAuthError("invalid webhook signature")

    if validate_stub_token(stub_token_header):
        return

    raise MobileMoneyWebhookAuthError(
        "unsigned mobile-money webhook rejected (configure provider secret or PAYMENT_STUB_TOKEN)"
    )
