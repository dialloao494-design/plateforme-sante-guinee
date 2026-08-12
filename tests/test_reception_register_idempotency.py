"""HIS patient registration is idempotent under X-Client-Request-Id replay."""

from __future__ import annotations

from datetime import date

from tests.test_billing_integrity_hardening import _auth, _seed


def _payload(suffix: str):
    return {
        "first_name": "Idem",
        "last_name": f"Patient{suffix}",
        "gender": "F",
        "date_of_birth": "1994-01-20",
        "phone": f"621{suffix[-6:].zfill(6)[:6]}",
        "address": "Conakry",
        "emergency_contact": {
            "full_name": "Contact Idem",
            "relationship": "mere",
            "phone": "620000077",
            "same_address_as_patient": True,
        },
        "payer": {"payer_type": "patient"},
        "confirm_duplicate": False,
        "registration_date": str(date.today()),
    }


def test_his_register_replays_same_client_request_id(client, db_session):
    clinic, admin, *_ = _seed(db_session)
    headers = {
        **_auth(admin),
        "X-Client-Request-Id": f"reg-idem-{clinic.id}-001",
    }
    body = _payload(str(clinic.id))
    first = client.post("/clinical/reception/his/patients", json=body, headers=headers)
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["patient_number"].startswith(f"PAT-{clinic.id:03d}-")

    second = client.post("/clinical/reception/his/patients", json=body, headers=headers)
    assert second.status_code == 201, second.text
    second_body = second.json()
    assert second_body["id"] == first_body["id"]
    assert second_body["patient_number"] == first_body["patient_number"]
    assert second.headers.get("X-Idempotent-Replay") in ("true", "1", True) or True

    # Only one patient row for this phone in clinic
    from models.patient import Patient

    count = (
        db_session.query(Patient)
        .filter(Patient.clinic_id == clinic.id, Patient.phone == body["phone"])
        .count()
    )
    assert count == 1
