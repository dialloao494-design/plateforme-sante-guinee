"""Medical history API coverage."""

from __future__ import annotations

import uuid

import models
from security import create_access_token, hash_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_medical_history_read_and_allergy_write(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"MH Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        doc_user = models.User(
            email=f"mh.doc.{suffix}@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db_session.add(doc_user)
        db_session.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="MH",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000444",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(doc_user)
        db_session.refresh(doctor)
        reception = models.User(
            email=f"mh.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.commit()
        db_session.refresh(reception)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Kadiatou", "last_name": "Barry", "age": 22, "gender": "F", "phone": f"+224622{suffix[:6]}"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]

    from datetime import datetime, timedelta

    slot = (datetime.now() + timedelta(days=2)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    assert r.status_code == 201

    r = client.get(f"/patients/{patient_id}/medical-history", headers=_auth(doc_user))
    assert r.status_code == 200
    assert r.json().get("medical_record") is not None

    r = client.post(
        f"/patients/{patient_id}/allergies",
        json={"allergen": "Pénicilline", "severity": "high", "notes": "Test"},
        headers=_auth(doc_user),
    )
    assert r.status_code == 201

    r = client.get(f"/patients/{patient_id}/timeline-grouped", headers=_auth(doc_user))
    assert r.status_code == 200
