"""Mobile Money webhooks."""
from __future__ import annotations
import json, logging
from fastapi import APIRouter, HTTPException, Request
from core.mobile_money_webhook_security import MobileMoneyWebhookAuthError, verify_mobile_money_signature
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payments/webhooks", tags=["Mobile Money Webhooks"])

@router.post("/orange-money")
async def orange_money_webhook(request: Request):
    raw = await request.body()
    sig = request.headers.get("X-Orange-Signature") or request.headers.get("X-Hub-Signature-256")
    try:
        verify_mobile_money_signature(provider="orange_gn", raw_body=raw, signature_header=sig, stub_token_header=request.headers.get("X-Payment-Stub-Token"))
    except MobileMoneyWebhookAuthError as e:
        raise HTTPException(status_code=403, detail="Webhook authentication failed") from e
    payload = json.loads(raw.decode() or "{}")
    return {"status": "accepted", "provider": "orange_gn", "reference": payload.get("reference") or payload.get("externalId")}

@router.post("/mtn-momo")
async def mtn_momo_webhook(request: Request):
    raw = await request.body()
    sig = request.headers.get("X-Callback-Signature") or request.headers.get("X-Hub-Signature-256")
    try:
        verify_mobile_money_signature(provider="mtn_gn", raw_body=raw, signature_header=sig, stub_token_header=request.headers.get("X-Payment-Stub-Token"))
    except MobileMoneyWebhookAuthError as e:
        raise HTTPException(status_code=403, detail="Webhook authentication failed") from e
    payload = json.loads(raw.decode() or "{}")
    return {"status": "accepted", "provider": "mtn_gn", "reference": payload.get("externalId") or payload.get("reference")}
