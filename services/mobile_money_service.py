"""
Orange Money / MTN Mobile Money integration layer (Guinea).

Clinic visit payments are collected at reception (cash / Orange Money).
This module describes optional mobile-money rails for future treasury integration.
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
    orange_live = _env_flag("ORANGE_MONEY_LIVE")
    mtn_live = _env_flag("MTN_MOMO_LIVE")
    return {
        "clinic_cashier": {
            "enabled": True,
            "notes": "Primary path: POST /clinical/billing/charges/{id}/pay (espèces / Orange Money).",
        },
        "mobile_money": {
            "orange_gn": {
                "status": "live" if orange_live else "stub",
                "callback_webhook": "/payments/webhooks/orange-money",
                "env": ["ORANGE_MONEY_LIVE", "ORANGE_MONEY_MERCHANT_ID", "ORANGE_MONEY_API_KEY", "ORANGE_MONEY_WEBHOOK_SECRET"],
            },
            "mtn_gn": {
                "status": "live" if mtn_live else "stub",
                "callback_webhook": "/payments/webhooks/mtn-momo",
                "env": ["MTN_MOMO_LIVE", "MTN_MOMO_SUBSCRIPTION_KEY", "MTN_MOMO_API_USER", "MTN_MOMO_API_KEY", "MTN_MOMO_WEBHOOK_SECRET"],
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
            else "Stub mode: treasury callback webhook required (live) or dev stub with X-Payment-Stub-Token when ALLOW_STUB_PAYMENT is enabled."
        ),
    }
