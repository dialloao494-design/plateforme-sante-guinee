"""Regression: registration must always return a real patient_number (N° dossier)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from models.patient import Patient
from tests.test_billing_integrity_hardening import _auth, _seed


def _registration_payload(**overrides):
    base = {
        "first_name": "Awa",
        "last_name": "Diallo",
        "gender": "F",
        "date_of_birth": "1995-04-12",
        "phone": "620111222",
        "address": "Conakry",
        "emergency_contact": {
            "full_name": "Mamadou Diallo",
            "relationship": "epoux",
            "phone": "620111223",
            "same_address_as_patient": True,
        },
        "payer": {"payer_type": "patient"},
        "confirm_duplicate": False,
        "registration_date": str(date.today()),
    }
    base.update(overrides)
    return base


def test_his_register_returns_patient_number(client, db_session):
    clinic, admin, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/patients",
        json=_registration_payload(),
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["patient_number"]
    assert body["patient_number"].startswith(f"PAT-{clinic.id:03d}-")
    assert body["qr_token"]
    # Row must not be left without dossier number
    row = db_session.query(Patient).filter(Patient.id == body["id"]).one()
    assert row.patient_number == body["patient_number"]


def test_his_register_never_flushes_null_patient_number(client, db_session):
    """Alembic 0028: patients.patient_number is NOT NULL — INSERT must not use NULL.

    Before the TMP-* provisional fix, create_patient flushed with patient_number=None
    and PostgreSQL rejected the insert (500 INTERNAL_ERROR on production).
    """
    clinic, admin, *_ = _seed(db_session)
    seen_before_flush: list[str | None] = []

    from sqlalchemy.orm import Session

    original_flush = Session.flush

    def tracking_flush(self, *args, **kwargs):
        for obj in list(self.new):
            if isinstance(obj, Patient):
                seen_before_flush.append(obj.patient_number)
                assert obj.patient_number is not None, (
                    "patient_number must be set before flush (NOT NULL constraint)"
                )
                assert str(obj.patient_number).startswith("TMP-"), (
                    f"expected provisional TMP-* dossier, got {obj.patient_number!r}"
                )
        return original_flush(self, *args, **kwargs)

    with patch.object(Session, "flush", tracking_flush):
        r = client.post(
            "/clinical/reception/his/patients",
            json=_registration_payload(
                first_name="Binta",
                last_name="Camara",
                phone="620333444",
                emergency_contact={
                    "full_name": "Ibrahima Camara",
                    "relationship": "pere",
                    "phone": "620333445",
                    "same_address_as_patient": True,
                },
            ),
            headers=_auth(admin),
        )

    assert r.status_code == 201, r.text
    assert seen_before_flush, "expected at least one Patient flush"
    body = r.json()
    assert body["patient_number"].startswith(f"PAT-{clinic.id:03d}-")
    row = db_session.query(Patient).filter(Patient.id == body["id"]).one()
    assert row.patient_number == body["patient_number"]
    assert not row.patient_number.startswith("TMP-")


def test_legacy_intake_never_flushes_null_patient_number(client, db_session):
    """The legacy CIS intake route must obey the same production constraint."""
    clinic, admin, *_ = _seed(db_session)
    seen_before_flush: list[str | None] = []

    from sqlalchemy.orm import Session

    original_flush = Session.flush

    def tracking_flush(self, *args, **kwargs):
        for obj in list(self.new):
            if isinstance(obj, Patient):
                seen_before_flush.append(obj.patient_number)
                assert obj.patient_number is not None
                assert str(obj.patient_number).startswith("TMP-")
        return original_flush(self, *args, **kwargs)

    with patch.object(Session, "flush", tracking_flush):
        response = client.post(
            "/clinical/reception/patients",
            json={
                "first_name": "Alpha",
                "last_name": "DeploySmoke",
                "age": 42,
                "gender": "F",
                "phone": "620555777",
            },
            headers=_auth(admin),
        )

    assert response.status_code == 201, response.text
    assert seen_before_flush
    body = response.json()
    assert body["patient_number"].startswith(f"PAT-{clinic.id:03d}-")
    row = db_session.query(Patient).filter(Patient.id == body["id"]).one()
    assert row.patient_number == body["patient_number"]
