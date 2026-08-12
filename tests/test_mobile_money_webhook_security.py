"""Mobile Money webhook HMAC fail-closed tests."""

from __future__ import annotations

import hashlib
import hmac
import json


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_orange_webhook_rejects_unsigned_in_production(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ORANGE_MONEY_LIVE", "true")
    monkeypatch.setenv("ORANGE_MONEY_WEBHOOK_SECRET", "orange-secret-test")
    body = {"reference": "PSG-1", "status": "SUCCESS"}
    raw = json.dumps(body).encode()
    res = client.post(
        "/payments/webhooks/orange-money",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 403


def test_orange_webhook_accepts_valid_signature(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ORANGE_MONEY_LIVE", "true")
    monkeypatch.setenv("ORANGE_MONEY_WEBHOOK_SECRET", "orange-secret-test")
    body = {"reference": "PSG-1", "status": "SUCCESS"}
    raw = json.dumps(body).encode()
    sig = _sign("orange-secret-test", raw)
    res = client.post(
        "/payments/webhooks/orange-money",
        content=raw,
        headers={"Content-Type": "application/json", "X-Orange-Signature": sig},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "accepted"


def test_mtn_webhook_rejects_invalid_signature(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MTN_MOMO_LIVE", "true")
    monkeypatch.setenv("MTN_MOMO_WEBHOOK_SECRET", "mtn-secret-test")
    body = {"externalId": "x1", "status": "SUCCESSFUL"}
    raw = json.dumps(body).encode()
    res = client.post(
        "/payments/webhooks/mtn-momo",
        content=raw,
        headers={"Content-Type": "application/json", "X-Callback-Signature": "deadbeef"},
    )
    assert res.status_code == 403


def test_mtn_webhook_accepts_valid_signature(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MTN_MOMO_LIVE", "true")
    monkeypatch.setenv("MTN_MOMO_WEBHOOK_SECRET", "mtn-secret-test")
    body = {"externalId": "x1", "status": "SUCCESSFUL"}
    raw = json.dumps(body).encode()
    sig = _sign("mtn-secret-test", raw)
    res = client.post(
        "/payments/webhooks/mtn-momo",
        content=raw,
        headers={"Content-Type": "application/json", "X-Callback-Signature": sig},
    )
    assert res.status_code == 200, res.text
    assert res.json()["provider"] == "mtn_gn"
