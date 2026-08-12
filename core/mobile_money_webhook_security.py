"""Mobile Money webhook HMAC verification."""
from __future__ import annotations
import hashlib, hmac, os
from core.payment_policy import validate_stub_token
class MobileMoneyWebhookAuthError(Exception): pass

def _live(p):
    f = "ORANGE_MONEY_LIVE" if p == "orange_gn" else "MTN_MOMO_LIVE"
    return (os.getenv(f) or "").strip().lower() in {"1","true","yes","on"}

def _secret(p):
    if p == "orange_gn":
        return (os.getenv("ORANGE_MONEY_WEBHOOK_SECRET") or os.getenv("ORANGE_MONEY_API_KEY") or "").strip()
    return (os.getenv("MTN_MOMO_WEBHOOK_SECRET") or os.getenv("MTN_MOMO_API_KEY") or "").strip()

def _norm(h):
    if not h: return ""
    s = str(h).strip()
    return s.split("=",1)[1].strip() if s.lower().startswith("sha256=") else s

def verify_mobile_money_signature(*, provider, raw_body, signature_header, stub_token_header=None):
    prod = (os.getenv("ENVIRONMENT") or "development").strip().lower() == "production"
    secret = _secret(provider)
    if prod or _live(provider):
        if not secret: raise MobileMoneyWebhookAuthError("secret not configured")
        sig = _norm(signature_header)
        if not sig: raise MobileMoneyWebhookAuthError("missing signature")
        exp = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(exp, sig): raise MobileMoneyWebhookAuthError("invalid signature")
        return
    if secret and _norm(signature_header):
        exp = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(exp, _norm(signature_header)): return
        raise MobileMoneyWebhookAuthError("invalid signature")
    if validate_stub_token(stub_token_header): return
    raise MobileMoneyWebhookAuthError("unsigned webhook rejected")
