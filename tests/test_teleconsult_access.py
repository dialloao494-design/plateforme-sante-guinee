"""Teleconsultation access window and authorization tests."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from services.teleconsultation_access import evaluate_teleconsult_room, validate_teleconsult_access


def _user(role: str, user_id: int = 1):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.email = f"{role}@test.com"
    return u


def _appointment(**kwargs):
    a = MagicMock()
    a.id = kwargs.get("id", 42)
    a.consultation_type = kwargs.get("consultation_type", "teleconsultation")
    a.status = kwargs.get("status", "confirmed")
    a.payment_status = kwargs.get("payment_status", "paid")
    a.date = kwargs.get("date", datetime.now() + timedelta(minutes=10))
    a.duration_minutes = kwargs.get("duration_minutes", 30)
    a.meeting_link = kwargs.get("meeting_link", None)
    a.doctor_id = kwargs.get("doctor_id", 10)
    a.patient_id = kwargs.get("patient_id", 20)
    return a


def _db_with_appointment(appointment, doctor=None, patient=None):
    db = MagicMock()

    def query(model):
        q = MagicMock()
        if model.__name__ == "RendezVous":
            q.filter.return_value.first.return_value = appointment
        elif model.__name__ == "Doctor" and doctor is not None:
            q.filter.return_value.first.return_value = doctor
        elif model.__name__ == "Patient" and patient is not None:
            q.filter.return_value.first.return_value = patient
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query
    return db


def test_expired_consultation_blocked():
    appt = _appointment(
        date=datetime.now() - timedelta(hours=3),
        status="confirmed",
    )
    db = _db_with_appointment(appt, doctor=MagicMock(id=10, user_id=1))
    with pytest.raises(HTTPException) as exc:
        validate_teleconsult_access(42, _user("doctor"), db)
    assert exc.value.status_code == 403


def test_cancelled_consultation_blocked():
    appt = _appointment(status="cancelled")
    db = _db_with_appointment(appt)
    with pytest.raises(HTTPException) as exc:
        validate_teleconsult_access(42, _user("patient"), db)
    assert exc.value.status_code == 403


def test_unauthorized_patient_blocked():
    appt = _appointment()
    db = _db_with_appointment(appt, patient=MagicMock(id=99, user_id=2))
    with pytest.raises(HTTPException) as exc:
        validate_teleconsult_access(42, _user("patient", user_id=1), db)
    assert exc.value.status_code == 403


def test_active_window_allows_join_with_local_clock():
    appt = _appointment(date=datetime.now() + timedelta(minutes=5))
    db = _db_with_appointment(appt, doctor=MagicMock(id=10, user_id=1))
    now = datetime.now()
    result = validate_teleconsult_access(42, _user("doctor"), db, now=now)
    assert result["can_join"] is True


def test_too_early_returns_soft_status():
    appt = _appointment(date=datetime.now() + timedelta(hours=2))
    db = _db_with_appointment(appt, doctor=MagicMock(id=10, user_id=1))
    status = evaluate_teleconsult_room(42, _user("doctor"), db)
    assert status["can_join"] is False
    assert status["reason"] == "too_early"


def test_local_naive_date_not_blocked_by_utc_skew():
    """Appointment stored as local naive must align with datetime.now() checks."""
    local_start = datetime.now() + timedelta(minutes=8)
    appt = _appointment(date=local_start)
    db = _db_with_appointment(appt, patient=MagicMock(id=20, user_id=1))
    status = evaluate_teleconsult_room(42, _user("patient", user_id=1), db, now=datetime.now())
    assert status["can_join"] is True


def test_access_payload_embed_fields():
    appt = _appointment(date=datetime.now() + timedelta(minutes=5))
    db = _db_with_appointment(appt, doctor=MagicMock(id=10, user_id=1))
    result = validate_teleconsult_access(42, _user("doctor"), db)
    assert result["provider"] == "jitsi"
    assert result["embed_mode"] == "jitsi_iframe"
    assert result["room_name"].startswith("sante-gn-42-")
    assert result["jitsi_domain"]
    assert result["display_name"]
    assert result["is_moderator"] is True
    assert result["embed_ready"] is True
    assert result["jitsi_embed_mode"] in ("self_hosted_open", "self_hosted_jwt", "jaas")
    assert result["meeting_url"] and result["room_name"] in result["meeting_url"]


def test_meet_jit_si_blocked_for_embed(monkeypatch):
    monkeypatch.setenv("JITSI_DOMAIN", "meet.jit.si")
    monkeypatch.delenv("JITSI_APP_ID", raising=False)
    monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
    from services.teleconsult_room import embed_block_reason, jitsi_embed_mode

    assert jitsi_embed_mode() == "blocked"
    assert embed_block_reason() is not None
    appt = _appointment(date=datetime.now() + timedelta(minutes=5))
    db = _db_with_appointment(appt, doctor=MagicMock(id=10, user_id=1))
    result = validate_teleconsult_access(42, _user("doctor"), db)
    assert result["embed_ready"] is False
    assert result["embed_block_reason"]


def test_meeting_link_matches_room_name():
    from services.teleconsult_room import meeting_link_for_appointment, room_name

    link = meeting_link_for_appointment(99)
    assert room_name(99) in link
    assert "consultation-99" not in link
