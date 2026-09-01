"""Phase 2 clinical modules — timeline, registers, monthly reports."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import models
from security import create_access_token, hash_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def _setup(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"P2 Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        nurse = models.User(
            email=f"nurse.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="nurse",
            clinic_id=clinic_id,
        )
        reception = models.User(
            email=f"recv.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add_all([nurse, reception])
        db_session.commit()
        db_session.refresh(nurse)
        db_session.refresh(reception)
    return clinic_id, nurse, reception


def test_nursing_register_and_timeline(client, db_session, admin_user):
    _clinic_id, nurse, reception = _setup(client, db_session, admin_user)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Fatou", "last_name": "Diallo", "age": 25, "gender": "F", "phone": "+224622111222"},
        headers=_auth(reception),
    )
    patient = r.json()
    patient_id = patient["id"]

    r = client.post(
        "/clinical/nursing-care/procedures",
        json={
            "patient_id": patient_id,
            "procedure_type": "injection",
            "procedure_date": date.today().isoformat(),
            "procedure_time": "09:30",
            "nurse_name": "Inf. Test",
            "notes": "BCG",
        },
        headers=_auth(nurse),
    )
    assert r.status_code == 201, r.text

    r = client.get(
        "/clinical/nursing-care/register",
        params={"year": date.today().year, "month": date.today().month},
        headers=_auth(nurse),
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1

    r = client.get(f"/clinical/patients/{patient_id}/timeline", headers=_auth(reception))
    assert r.status_code == 200
    body = r.json()
    assert body["patient_id"] == patient_id
    assert body["patient"]["patient_number"] == patient["patient_number"]
    assert body["patient"]["age"] == patient["age"]
    assert any(e["module"] == "nursing" for e in body["events"])

    with provisioning_channel("test_fixture"):
        pev_agent = models.User(
            email=f"pev.{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="pev_agent",
            clinic_id=_clinic_id,
        )
        db_session.add(pev_agent)
        db_session.commit()
        db_session.refresh(pev_agent)

    search = client.get(
        "/clinical/reception/patients",
        params={"q": patient["patient_number"]},
        headers=_auth(pev_agent),
    )
    assert search.status_code == 200
    journey = client.get(f"/clinical/patients/{patient_id}/journey", headers=_auth(pev_agent))
    assert journey.status_code == 200


def test_nutrition_register_json_serializable(client, db_session, admin_user):
    clinic_id, nurse, reception = _setup(client, db_session, admin_user)
    with provisioning_channel("test_fixture"):
        nutritionist = models.User(
            email=f"nutri2.{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="nutritionist",
            clinic_id=clinic_id,
        )
        db_session.add(nutritionist)
        db_session.commit()
        db_session.refresh(nutritionist)
    r = client.post(
        "/clinical/reception/patients",
        json={
            "first_name": "Child",
            "last_name": "Nutri",
            "age": 3,
            "gender": "M",
            "phone": "+224622333444",
            "date_of_birth": (date.today() - timedelta(days=365 * 3)).isoformat(),
        },
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    client.post(
        "/clinical/nutrition/assessments",
        json={"patient_id": patient_id, "weight_kg": 14.0, "height_cm": 95, "muac_cm": 14.5, "recommendations": "Test"},
        headers=_auth(nutritionist),
    )
    reg = client.get(
        "/clinical/nutrition/register",
        params={"year": date.today().year, "month": date.today().month},
        headers=_auth(nutritionist),
    )
    assert reg.status_code == 200, reg.text
    assert len(reg.json()) >= 1
    row = reg.json()[0]
    assert "patient" in row and "record" in row
    if row["patient"].get("date_of_birth"):
        assert isinstance(row["patient"]["date_of_birth"], str)


def test_koloma_monthly_reports(client, db_session, admin_user):
    clinic_id, nurse, reception = _setup(client, db_session, admin_user)
    admin_user.clinic_id = clinic_id
    db_session.commit()

    r = client.get(
        "/clinical/reports/koloma/monthly",
        params={"year": date.today().year, "month": date.today().month},
        headers=_auth(admin_user),
    )
    assert r.status_code == 200
    data = r.json()
    for key in ("pev", "nursing", "hospitalization", "nutrition", "laboratory", "pharmacy"):
        assert key in data


def test_lab_and_pharmacy_dashboards(client, db_session, admin_user):
    clinic_id, _nurse, reception = _setup(client, db_session, admin_user)
    with provisioning_channel("test_fixture"):
        lab = models.User(
            email=f"lab.{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="lab_technician",
            clinic_id=clinic_id,
        )
        pharmacist = models.User(
            email=f"ph.{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="pharmacist",
            clinic_id=clinic_id,
        )
        db_session.add_all([lab, pharmacist])
        db_session.commit()

    r = client.get("/clinical/lab/catalog", headers=_auth(lab))
    assert r.status_code == 200
    assert len(r.json().get("tests", [])) >= 5

    r = client.get("/clinical/lab/dashboard", headers=_auth(lab))
    assert r.status_code == 200

    r = client.get("/clinical/pharmacy/dashboard", headers=_auth(pharmacist))
    assert r.status_code == 200

    report = client.get(
        "/clinical/pharmacy/reports/monthly",
        params={"year": date.today().year, "month": date.today().month},
        headers=_auth(pharmacist),
    )
    assert report.status_code == 200
    assert {
        "unique_patients",
        "requests_created",
        "total_dispensed",
        "generated_revenue_gnf",
        "collected_revenue_gnf",
        "pending_revenue_gnf",
        "collection_rate_percent",
        "top_medications",
        "register_rows",
    } <= report.json().keys()

    r = client.get(
        "/clinical/workflow/queue/nursing",
        headers=_auth(reception),
    )
    assert r.status_code == 200
