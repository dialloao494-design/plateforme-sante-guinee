"""
Orange Money / MTN Mobile Money integration layer (Guinea).

This module centralises configuration and initiation. Live HTTP calls to
Orange/MTN APIs are deferred behind env flags so the platform can ship with
Stripe while Mobile Money is progressively enabled in production.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any, Literal

Provider = Literal["orange_gn", "mtn_gn"]


def _env_flag(name: str) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def describe_rails() -> dict[str, Any]:
    stripe_on = bool(os.getenv("STRIPE_SECRET_KEY") or os.getenv("STRIPE_API_KEY"))
    orange_live = _env_flag("ORANGE_MONEY_LIVE")
    mtn_live = _env_flag("MTN_MOMO_LIVE")
    return {
        "stripe": {
            "enabled": stripe_on,
            "checkout": stripe_on,
            "notes": "Hosted Checkout / webhooks when STRIPE_* configured.",
        },
        "mobile_money": {
            "orange_gn": {
                "status": "live" if orange_live else "stub",
                "callback_webhook": "/payments/webhooks/orange-money",
                "env": ["ORANGE_MONEY_LIVE", "ORANGE_MONEY_MERCHANT_ID", "ORANGE_MONEY_API_KEY"],
            },
            "mtn_gn": {
                "status": "live" if mtn_live else "stub",
                "callback_webhook": "/payments/webhooks/mtn-momo",
                "env": ["MTN_MOMO_LIVE", "MTN_MOMO_SUBSCRIPTION_KEY", "MTN_MOMO_API_USER", "MTN_MOMO_API_KEY"],
            },
        },
    }


def initiate_collection_stub(
    *,
    appointment_id: int,
    provider: Provider,
    amount_gnf: float,
    msisdn: str | None,
) -> dict[str, Any]:
    """
    Returns a provider-agnostic payload. When *_LIVE flags are false, no
    external HTTP call is made — suitable for UAT and cabinet demos.
    """
    reference = f"PSG-{appointment_id}-{uuid.uuid4().hex[:10].upper()}"
    live = _env_flag("ORANGE_MONEY_LIVE") if provider == "orange_gn" else _env_flag("MTN_MOMO_LIVE")
    masked = None
    if msisdn and len(msisdn) >= 4:
        masked = f"{'*' * max(0, len(msisdn) - 4)}{msisdn[-4:]}"
    return {
        "status": "pending",
        "provider": provider,
        "reference": reference,
        "amount_gnf": amount_gnf,
        "msisdn_masked": masked,
        "live_mode": live,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "next_step": (
            "POST confirmation to /payments/mobile-money/confirm when operator callback validates payment."
            if live
            else "Stub mode: use POST /payments/{id}/confirm-payment after manual treasury validation."
        ),
    }
