"""
Payment settlement policy — which channels may mark an appointment as paid.

Public HTTP clients must never settle via an implicit stub; Stripe proof or admin ops only.
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache

from core.settings import get_settings

# Channels that may transition appointment → paid + confirmed.
SETTLEMENT_CHANNEL_STRIPE_CHECKOUT = "stripe_checkout"
SETTLEMENT_CHANNEL_STRIPE_WEBHOOK = "stripe_webhook"
SETTLEMENT_CHANNEL_ADMIN_MANUAL = "admin_manual"
SETTLEMENT_CHANNEL_DEV_STUB = "dev_stub"

AUTHORIZED_SETTLEMENT_CHANNELS = frozenset(
    {
        SETTLEMENT_CHANNEL_STRIPE_CHECKOUT,
        SETTLEMENT_CHANNEL_STRIPE_WEBHOOK,
        SETTLEMENT_CHANNEL_ADMIN_MANUAL,
        SETTLEMENT_CHANNEL_DEV_STUB,
    }
)


class PaymentPolicyError(ValueError):
    """Invalid or disallowed settlement channel / evidence."""


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def payment_stub_token() -> str:
    return (os.getenv("PAYMENT_STUB_TOKEN") or "").strip()


def is_stub_settlement_allowed() -> bool:
    """
    Dev/staging stub settlements (manual treasury simulation).

    Never enabled in production — even if ALLOW_STUB_PAYMENT is mistakenly set.
    """
    settings = get_settings()
    if settings.is_production:
        return False
    return _env_flag("ALLOW_STUB_PAYMENT", default=False)


def validate_stub_token(provided: str | None) -> bool:
    expected = payment_stub_token()
    if not expected or not provided:
        return False
    return secrets.compare_digest(expected.strip(), provided.strip())


def assert_settlement_channel(channel: str) -> str:
    normalized = (channel or "").strip().lower()
    if normalized not in AUTHORIZED_SETTLEMENT_CHANNELS:
        raise PaymentPolicyError(
            f"Unknown settlement channel '{channel}'. "
            f"Allowed: {', '.join(sorted(AUTHORIZED_SETTLEMENT_CHANNELS))}"
        )
    return normalized
