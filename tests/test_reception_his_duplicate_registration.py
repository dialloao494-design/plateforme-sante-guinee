"""Regression: reception HIS registration must expose duplicate_patient 409
and allow confirm_duplicate — the production clinic blocker when staff re-enter
a known phone / name+DOB without a confirm path in the UI.
"""

from __future__ import annotations

import uuid

import models
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides):
    base = {
        "first_name": "Aissatou",
        "last_name": "Bah",
        "gender": "F",
        "date_of_birth": "1992-08-15",
        "date_of_birth_precision": "full",
        "phone": "622111222",
        "address": "Ratoma",
        "emergency_contact": {
            "full_name": "Ibrahima Bah",
            "relationship": "Père",
            "phone": "622333444",
        },
        "payer": {"payer_type": "patient"},
        "confirm_duplicate": False,
    }
    base.update(overrides)
    return base


def test_reception_his_duplicate_registration_requires_confirm(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Dup Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    assert r.status_code == 201, r.text
    clinic_id = r.json()["id"]

    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"dup.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.flush()
        db_session.add(
            models.ClinicStaff(clinic_id=clinic_id, user_id=reception.id, is_active=True)
        )
        db_session.commit()
        db_session.refresh(reception)

    phone = f"622{suffix[:6]}"
    create = client.post(
        "/clinical/reception/his/patients",
        json=_payload(phone=phone, last_name=f"Bah{suffix}"),
        headers=_auth(reception),
    )
    assert create.status_code == 201, create.text
    first = create.json()
    assert first["patient_number"]

    dup = client.post(
        "/clinical/reception/his/patients",
        json=_payload(phone=phone, last_name=f"Bah{suffix}"),
        headers=_auth(reception),
    )
    assert dup.status_code == 409, dup.text
    detail = dup.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["code"] == "duplicate_patient"
    assert "similaires" in detail["message"].lower() or "déjà" in detail["message"].lower()
    assert detail["matches"]
    assert detail["matches"][0]["id"] == first["id"]
    assert "phone" in detail["matches"][0]["match_reasons"]

    confirmed = client.post(
        "/clinical/reception/his/patients",
        json=_payload(phone=phone, last_name=f"Bah{suffix}", confirm_duplicate=True),
        headers=_auth(reception),
    )
    assert confirmed.status_code == 201, confirmed.text
    second = confirmed.json()
    assert second["id"] != first["id"]
    assert second["patient_number"] != first["patient_number"]

    search = client.get(
        "/clinical/reception/his/patients/search",
        params={"q": second["patient_number"]},
        headers=_auth(reception),
    )
    assert search.status_code == 200, search.text
    assert any(p["id"] == second["id"] for p in search.json())

    opened = client.get(
        f"/clinical/reception/his/patients/{second['id']}",
        headers=_auth(reception),
    )
    assert opened.status_code == 200, opened.text
    assert opened.json()["id"] == second["id"]
