"""Nutrition, immunization (PEV), staff list, and password reset."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import models
from security import create_access_token, hash_password, verify_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def _clinical_setup(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"P1 Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        nutritionist = models.User(
            email=f"nutri.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1!"),
            role="nutritionist",
            clinic_id=clinic_id,
        )
        midwife = models.User(
            email=f"midwife.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1!"),
            role="midwife",
            clinic_id=clinic_id,
        )
        reception = models.User(
            email=f"recv.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add_all([nutritionist, midwife, reception])
        db_session.commit()
        db_session.refresh(nutritionist)
        db_session.refresh(midwife)
        db_session.refresh(reception)
    return clinic_id, nutritionist, midwife, reception


def test_nutrition_assessment_and_history(client, db_session, admin_user):
    clinic_id, nutritionist, _midwife, reception = _clinical_setup(client, db_session, admin_user)

    r = client.post(
        "/clinical/reception/patients",
        json={
            "first_name": "Aissatou",
            "last_name": "Camara",
            "age": 2,
            "gender": "F",
            "phone": "+224622000222",
            "date_of_birth": (date.today() - timedelta(days=730)).isoformat(),
        },
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]

    r = client.post(
        "/clinical/nutrition/assessments",
        json={
            "patient_id": patient_id,
            "weight_kg": 10.5,
            "height_cm": 82.0,
            "muac_cm": 13.0,
            "age_months": 24,
        },
        headers=_auth(nutritionist),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nutritional_status"] == "normal"

    r = client.get(
        f"/clinical/nutrition/patients/{patient_id}/history",
        headers=_auth(nutritionist),
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_immunization_schedule_due_missed(client, db_session, admin_user):
    clinic_id, _nutritionist, midwife, reception = _clinical_setup(client, db_session, admin_user)

    r = client.get("/clinical/immunization/schedule", headers=_auth(midwife))
    assert r.status_code == 200
    schedule = r.json()
    assert len(schedule) >= 10

    r = client.post(
        "/clinical/reception/patients",
        json={
            "first_name": "Mamadou",
            "last_name": "Bah",
            "age": 0,
            "gender": "M",
            "phone": "+224622000333",
            "date_of_birth": (date.today() - timedelta(days=120)).isoformat(),
        },
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]

    r = client.get(
        f"/clinical/immunization/patients/{patient_id}/status",
        headers=_auth(midwife),
    )
    assert r.status_code == 200
    status = r.json()
    assert "due" in status and "missed" in status

    first = schedule[0]
    r = client.post(
        "/clinical/immunization/records",
        json={
            "patient_id": patient_id,
            "vaccine_code": first["vaccine_code"],
            "vaccine_name": first["vaccine_name"],
            "dose_label": first["dose_label"],
            "administered_at": date.today().isoformat(),
            "batch_number": "LOT-TEST-01",
            "vaccine_expiry_date": (date.today() + timedelta(days=180)).isoformat(),
            "injection_site": "deltoide_d",
            "vaccination_strategy": "routine",
            "vaccinator_name": "Agent PEV Test",
        },
        headers=_auth(midwife),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["batch_number"] == "LOT-TEST-01"
    assert body["injection_site"] == "deltoide_d"
    assert body["age_at_vaccination_months"] is not None

    r = client.get(
        f"/clinical/immunization/patients/{patient_id}/history",
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(
        "/clinical/immunization/register",
        params={"year": date.today().year, "month": date.today().month},
        headers=_auth(midwife),
    )
    assert r.status_code == 200
    register = r.json()
    assert len(register) >= 1
    assert register[0]["patient"]["first_name"] == "Mamadou"
    assert register[0]["line_number"] == 1

    r = client.get(f"/clinical/patients/{patient_id}/journey", headers=_auth(reception))
    assert r.status_code == 200
    journey = r.json()
    assert len(journey.get("immunizations", [])) == 1


def test_list_clinic_staff(client, db_session, admin_user):
    clinic_id, nutritionist, midwife, reception = _clinical_setup(client, db_session, admin_user)

    r = client.get(
        "/clinical/staff",
        params={"clinic_id": clinic_id},
        headers=_auth(admin_user),
    )
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert nutritionist.email in emails
    assert midwife.email in emails
    assert reception.email in emails

    r = client.get(
        "/clinical/staff",
        params={"clinic_id": clinic_id, "role": "nutritionist"},
        headers=_auth(admin_user),
    )
    assert r.status_code == 200
    assert all(u["role"] == "nutritionist" for u in r.json())


def test_password_reset_flow(client, db_session):
    suffix = uuid.uuid4().hex[:8]
    user = models.User(
        email=f"reset.{suffix}@test.com",
        hashed_password=hash_password("OldPass1!"),
        role="patient",
    )
    db_session.add(user)
    db_session.commit()

    r = client.post("/auth/forgot-password", json={"email": user.email})
    assert r.status_code == 200

    from services.password_reset_service import create_reset_token

    raw = create_reset_token(db_session, email=user.email)
    assert raw

    r = client.post("/auth/reset-password", json={"token": raw, "new_password": "NewSecure12!"})
    assert r.status_code == 200

    db_session.refresh(user)
    assert verify_password("NewSecure12!", user.hashed_password)
