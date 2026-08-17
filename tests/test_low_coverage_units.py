"""Unit coverage for previously untested infrastructure helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from core.attachment_malware import EICAR_SIGNATURE, scan_attachment_bytes
from services.mobile_money_service import describe_rails, initiate_collection_stub
from services.notification_delivery import describe_notification_channels, record_in_app_notification


@pytest.mark.parametrize("mode", ["off", "0", "false", "disabled", ""])
def test_malware_scanner_disabled_modes_accept_content(monkeypatch, mode):
    monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", mode)
    scan_attachment_bytes(EICAR_SIGNATURE, filename="eicar.com")


def test_malware_stub_rejects_eicar_and_accepts_clean_content(monkeypatch):
    monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "stub")
    with pytest.raises(HTTPException) as raised:
        scan_attachment_bytes(EICAR_SIGNATURE, filename="eicar.com")
    assert raised.value.status_code == 400
    scan_attachment_bytes(b"clean clinical document", filename="result.txt")


def test_malware_clamav_mode_fails_closed_without_scanner(monkeypatch):
    monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "clamav")
    monkeypatch.setattr("core.attachment_malware.shutil.which", lambda name: None)
    with pytest.raises(HTTPException) as raised:
        scan_attachment_bytes(b"content", filename="result.pdf")
    assert raised.value.status_code == 503


def test_unknown_malware_mode_does_not_block_upload(monkeypatch):
    monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "future-scanner")
    scan_attachment_bytes(b"content")


def test_mobile_money_rail_flags_follow_environment(monkeypatch):
    monkeypatch.setenv("ORANGE_MONEY_LIVE", "true")
    monkeypatch.setenv("MTN_MOMO_LIVE", "false")
    rails = describe_rails()["mobile_money"]
    assert rails["orange_gn"]["status"] == "live"
    assert rails["mtn_gn"]["status"] == "stub"


@pytest.mark.parametrize("provider", ["orange_gn", "mtn_gn"])
def test_mobile_money_stub_masks_phone_and_creates_unique_reference(monkeypatch, provider):
    monkeypatch.delenv("ORANGE_MONEY_LIVE", raising=False)
    monkeypatch.delenv("MTN_MOMO_LIVE", raising=False)
    first = initiate_collection_stub(
        appointment_id=17,
        provider=provider,
        amount_gnf=150_000,
        msisdn="+224620123456",
    )
    second = initiate_collection_stub(
        appointment_id=17,
        provider=provider,
        amount_gnf=150_000,
        msisdn="+224620123456",
    )
    assert first["reference"].startswith("PSG-17-")
    assert first["reference"] != second["reference"]
    assert first["msisdn_masked"].endswith("3456")
    assert "620123" not in first["msisdn_masked"]
    assert first["live_mode"] is False


def test_notification_channel_capabilities(monkeypatch):
    for name in ("SMS_PROVIDER_URL", "TWILIO_ACCOUNT_SID", "SMTP_HOST", "RESEND_API_KEY", "VAPID_PUBLIC_KEY", "WEB_PUSH_PUBLIC_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert describe_notification_channels()["enabled"] is False
    monkeypatch.setenv("RESEND_API_KEY", "configured")
    result = describe_notification_channels()
    assert result["enabled"] is True
    assert {row["id"]: row["status"] for row in result["channels"]}["email"] == "live"


class _FailingNotificationDb:
    rolled_back = False

    def add(self, row):
        raise RuntimeError("write failed")

    def rollback(self):
        self.rolled_back = True


def test_notification_record_failure_rolls_back():
    db = _FailingNotificationDb()
    result = record_in_app_notification(
        db,
        user_id=1,
        subject="Subject",
        body="Body",
    )
    assert result is None
    assert db.rolled_back is True


class _SuccessfulNotificationDb:
    def __init__(self):
        self.row = None

    def add(self, row):
        self.row = row

    def commit(self):
        self.row.id = 9

    def refresh(self, row):
        pass


def test_notification_record_truncates_external_fields():
    db = _SuccessfulNotificationDb()
    row = record_in_app_notification(
        db,
        user_id=1,
        subject="s" * 300,
        body="Body",
        meta={"value": "x" * 2000},
    )
    assert row is db.row
    assert len(row.subject) == 255
    assert len(row.meta) == 1024
