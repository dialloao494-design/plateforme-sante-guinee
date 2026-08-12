import hashlib,hmac,json,pytest
from core.mobile_money_webhook_security import MobileMoneyWebhookAuthError, verify_mobile_money_signature

def _s(sec,b): return hmac.new(sec.encode(),b,hashlib.sha256).hexdigest()

def test_unsigned_prod(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT","production")
    monkeypatch.setenv("ORANGE_MONEY_WEBHOOK_SECRET","orange-webhook-secret-32chars-min")
    assert client.post("/payments/webhooks/orange-money", content=b"{}").status_code==403

def test_signed(client, monkeypatch):
    sec="orange-webhook-secret-32chars-min"; monkeypatch.setenv("ENVIRONMENT","development"); monkeypatch.setenv("ORANGE_MONEY_WEBHOOK_SECRET",sec)
    body=json.dumps({"reference":"R1"}).encode()
    r=client.post("/payments/webhooks/orange-money", content=body, headers={"X-Orange-Signature":f"sha256={_s(sec,body)}"})
    assert r.status_code==200

def test_live_secret(monkeypatch):
    monkeypatch.setenv("ORANGE_MONEY_LIVE","true")
    with pytest.raises(MobileMoneyWebhookAuthError):
        verify_mobile_money_signature(provider="orange_gn", raw_body=b"{}", signature_header="x")
