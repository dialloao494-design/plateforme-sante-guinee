"""Teleconsultation access window and authorization tests."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from services.teleconsultation_access import validate_teleconsult_access


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
    a.date = kwargs.get("date", datetime.utcnow())
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
        date=datetime.utcnow() - timedelta(hours=3),
        status="confirmed",
    )
    db = _db_with_appointment(appt)
    doc = MagicMock(id=10, user_id=1)
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
