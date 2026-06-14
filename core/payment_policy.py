"""
Payment settlement policy — admin manual and dev stub only (in-clinic billing uses clinical API).
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache

from core.settings import get_settings

SETTLEMENT_CHANNEL_ADMIN_MANUAL = "admin_manual"
SETTLEMENT_CHANNEL_DEV_STUB = "dev_stub"

AUTHORIZED_SETTLEMENT_CHANNELS = frozenset(
    {
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


DEMO_STAGING_STUB_TOKEN = "demo_plateforme_sante_guinee_stub_v1"


@lru_cache(maxsize=1)
def payment_stub_token() -> str:
    token = (os.getenv("PAYMENT_STUB_TOKEN") or "").strip()
    if token:
        return token
    if is_stub_settlement_allowed() and get_settings().is_staging:
        return DEMO_STAGING_STUB_TOKEN
    return ""


def is_stub_settlement_allowed() -> bool:
    settings = get_settings()
    if settings.is_production:
        return False
    return _env_flag("ALLOW_STUB_PAYMENT", default=False)


def validate_stub_token(provided: str | None) -> bool:
    provided_clean = (provided or "").strip()
    if not provided_clean:
        return False
    expected = payment_stub_token()
    if expected and secrets.compare_digest(expected, provided_clean):
        return True
    settings = get_settings()
    if settings.is_staging and is_stub_settlement_allowed():
        return secrets.compare_digest(DEMO_STAGING_STUB_TOKEN, provided_clean)
    return False


def assert_settlement_channel(channel: str) -> str:
    normalized = (channel or "").strip().lower()
    if normalized not in AUTHORIZED_SETTLEMENT_CHANNELS:
        raise PaymentPolicyError(
            f"Unknown settlement channel '{channel}'. "
            f"Allowed: {', '.join(sorted(AUTHORIZED_SETTLEMENT_CHANNELS))}"
        )
    return normalized
