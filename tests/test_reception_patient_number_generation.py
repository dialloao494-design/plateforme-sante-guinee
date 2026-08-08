"""Regression: registration must always return a real patient_number (N° dossier)."""

from __future__ import annotations

from datetime import date

from tests.test_billing_integrity_hardening import _auth, _seed


def test_his_register_returns_patient_number(client, db_session):
    clinic, admin, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/patients",
        json={
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
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["patient_number"]
    assert body["patient_number"].startswith(f"PAT-{clinic.id:03d}-")
    assert body["qr_token"]
    # Row must not be left without dossier number
    from models.patient import Patient

    row = db_session.query(Patient).filter(Patient.id == body["id"]).one()
    assert row.patient_number == body["patient_number"]
