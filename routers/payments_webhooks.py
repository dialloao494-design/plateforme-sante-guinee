"""Mobile Money operator webhooks — Orange Money Guinea and MTN MoMo."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request

from core.mobile_money_webhook_security import (
    MobileMoneyWebhookAuthError,
    verify_mobile_money_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments/webhooks", tags=["Mobile Money Webhooks"])


def _parse_body(raw_body: bytes) -> dict:
    try:
        return json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc


@router.post("/orange-money")
async def orange_money_webhook(request: Request):
    """
    Orange Money Guinea payment status callback.

    Requires HMAC-SHA256 in ``X-Orange-Signature`` (or ``X-Hub-Signature-256``)
    when ``ORANGE_MONEY_LIVE=true`` or in production.
    """
    raw_body = await request.body()
    signature = (
        request.headers.get("X-Orange-Signature")
        or request.headers.get("x-orange-signature")
        or request.headers.get("X-Hub-Signature-256")
        or request.headers.get("x-hub-signature-256")
    )
    stub_token = request.headers.get("X-Payment-Stub-Token") or request.headers.get(
        "x-payment-stub-token"
    )
    try:
        verify_mobile_money_signature(
            provider="orange_gn",
            raw_body=raw_body,
            signature_header=signature,
            stub_token_header=stub_token,
        )
    except MobileMoneyWebhookAuthError as exc:
        raise HTTPException(status_code=403, detail="Webhook authentication failed") from exc

    payload = _parse_body(raw_body)
    reference = (
        payload.get("reference")
        or payload.get("externalId")
        or payload.get("order_id")
        or payload.get("transaction_id")
    )
    status_value = str(payload.get("status") or payload.get("payment_status") or "received").lower()
    logger.info(
        "Orange Money webhook accepted reference=%s status=%s",
        reference,
        status_value,
    )
    return {
        "status": "accepted",
        "provider": "orange_gn",
        "reference": reference,
        "payment_status": status_value,
    }


@router.post("/mtn-momo")
async def mtn_momo_webhook(request: Request):
    """
    MTN MoMo payment status callback.

    Requires HMAC-SHA256 in ``X-Callback-Signature`` when ``MTN_MOMO_LIVE=true``
    or in production.
    """
    raw_body = await request.body()
    signature = (
        request.headers.get("X-Callback-Signature")
        or request.headers.get("x-callback-signature")
        or request.headers.get("X-Hub-Signature-256")
        or request.headers.get("x-hub-signature-256")
    )
    stub_token = request.headers.get("X-Payment-Stub-Token") or request.headers.get(
        "x-payment-stub-token"
    )
    try:
        verify_mobile_money_signature(
            provider="mtn_gn",
            raw_body=raw_body,
            signature_header=signature,
            stub_token_header=stub_token,
        )
    except MobileMoneyWebhookAuthError as exc:
        raise HTTPException(status_code=403, detail="Webhook authentication failed") from exc

    payload = _parse_body(raw_body)
    reference = (
        payload.get("externalId")
        or payload.get("reference")
        or payload.get("financialTransactionId")
        or payload.get("transaction_id")
    )
    status_value = str(payload.get("status") or payload.get("payment_status") or "received").lower()
    logger.info(
        "MTN MoMo webhook accepted reference=%s status=%s",
        reference,
        status_value,
    )
    return {
        "status": "accepted",
        "provider": "mtn_gn",
        "reference": reference,
        "payment_status": status_value,
    }
