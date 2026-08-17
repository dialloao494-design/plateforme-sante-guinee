"""Regression tests for defects found during the whole-repository audit."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routers.notifications import list_notifications
from services.availability_service import AvailabilityService


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class _AvailabilityDb:
    def __init__(self, slot):
        self.slot = slot

    def query(self, model):
        return _Query(self.slot)


def test_availability_rejects_appointment_crossing_midnight():
    slot = SimpleNamespace(start_time=time(8), end_time=time(23, 59))
    allowed, message = AvailabilityService.is_appointment_within_working_hours(
        doctor_id=1,
        appointment_start=datetime(2026, 8, 17, 23, 30),
        duration_minutes=90,
        db=_AvailabilityDb(slot),
    )
    assert allowed is False
    assert "another day" in message


@pytest.mark.parametrize("duration", [0, -15])
def test_availability_rejects_non_positive_duration(duration):
    allowed, message = AvailabilityService.is_appointment_within_working_hours(
        doctor_id=1,
        appointment_start=datetime(2026, 8, 17, 10),
        duration_minutes=duration,
        db=_AvailabilityDb(None),
    )
    assert allowed is False
    assert "greater than zero" in message


def test_availability_accepts_same_day_slot():
    slot = SimpleNamespace(start_time=time(8), end_time=time(17))
    allowed, message = AvailabilityService.is_appointment_within_working_hours(
        doctor_id=1,
        appointment_start=datetime(2026, 8, 17, 10),
        duration_minutes=30,
        db=_AvailabilityDb(slot),
    )
    assert allowed is True
    assert message == ""


class _BrokenNotificationDb:
    def query(self, model):
        raise RuntimeError("database password must not leak")


def test_notification_database_failure_is_503_and_opaque():
    with pytest.raises(HTTPException) as raised:
        list_notifications(
            db=_BrokenNotificationDb(),
            current_user=SimpleNamespace(id=42),
        )
    assert raised.value.status_code == 503
    assert "password" not in raised.value.detail


def _whatsapp_signature(secret: str, raw: bytes) -> str:
    digest = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_whatsapp_processing_failure_returns_retryable_opaque_error(client, monkeypatch):
    secret = "whatsapp-regression-secret"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)

    def fail_processing(*args, **kwargs):
        raise RuntimeError("sensitive database failure")

    monkeypatch.setattr(
        "routers.reminders.ReminderService.handle_patient_response",
        fail_processing,
    )
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "+224600000001",
                        "text": {"body": "CONFIRMER"},
                        "context": {"appointment_id": 123},
                    }]
                }
            }]
        }]
    }
    raw = json.dumps(payload).encode()
    response = client.post(
        "/clinical/reminders/whatsapp/webhook",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": _whatsapp_signature(secret, raw),
        },
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Webhook processing temporarily unavailable"}
    assert "sensitive" not in response.text
