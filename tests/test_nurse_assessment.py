"""Tests for nurse assessment API."""

from datetime import date, datetime

import models
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password


def _seed_nurse_clinic(db_session, admin_user, salt=""):
    suffix = f"{admin_user.id}{salt}"
    clinic = models.Clinic(name=f"Nurse Clinic {suffix}", address="Test")
    db_session.add(clinic)
    db_session.flush()

    nurse = models.User(
        email=f"nurse.{suffix}@test.com",
        hashed_password=hash_password("NurseTest1!"),
        role="nurse",
        clinic_id=clinic.id,
    )
    doctor_user = models.User(
        email=f"doc.{suffix}@test.com",
        hashed_password=hash_password("DoctorTest1!"),
        role="doctor",
        clinic_id=clinic.id,
    )
    with provisioning_channel("test_fixture"):
        db_session.add_all([nurse, doctor_user])
        db_session.flush()

    doctor = models.Doctor(
        user_id=doctor_user.id,
        clinic_id=clinic.id,
        first_name="Dr",
        last_name="Test",
        specialty="general",
        city="Conakry",
        phone="620000000",
    )
    patient = models.Patient(
        clinic_id=clinic.id,
        first_name="Aminata",
        last_name="Diallo",
        gender="F",
        age=32,
        date_of_birth=date(1993, 1, 1),
        patient_number=f"P{suffix}",
        phone="620000001",
    )
    db_session.add_all([doctor, patient])
    db_session.commit()
    db_session.refresh(nurse)
    db_session.refresh(doctor_user)
    db_session.refresh(doctor)
    db_session.refresh(patient)
    return clinic.id, nurse, doctor_user, doctor, patient


def _auth(user):
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_nurse_assessment_save_and_doctor_sync(client, db_session, admin_user):
    clinic_id, nurse, doctor_user, doctor, patient = _seed_nurse_clinic(db_session, admin_user)

    r = client.post(
        "/clinical/nurse/assessments",
        headers=_auth(nurse),
        json={
            "patient_id": patient.id,
            "temperature_c": 37.8,
            "bp_systolic": 120,
            "bp_diastolic": 80,
            "heart_rate": 78,
            "respiratory_rate": 16,
            "height_cm": 165,
            "weight_kg": 60,
            "reason_for_consultation": "Douleur thoracique",
            "allergies": "Aspirine",
            "nurse_notes": "Patient anxieux",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reason_for_consultation"] == "Douleur thoracique"
    assert body["bmi"] == 22.0

    r2 = client.get(
        f"/clinical/nurse/patients/{patient.id}/assessment",
        headers=_auth(nurse),
    )
    assert r2.status_code == 200
    assert r2.json()["allergies"] == "Aspirine"

    rdv = models.RendezVous(
        clinic_id=clinic_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        date=datetime.utcnow(),
        status="scheduled",
        clinical_status="checked_in",
    )
    db_session.add(rdv)
    db_session.commit()
    db_session.refresh(rdv)

    r3 = client.post(
        "/clinical/consultations",
        headers=_auth(doctor_user),
        json={"appointment_id": rdv.id, "chief_complaint": "fallback"},
    )
    assert r3.status_code in (200, 201), r3.text
    consult = r3.json()
    assert "Douleur thoracique" in (consult.get("chief_complaint") or "")
    assert "Aspirine" in (consult.get("history") or "")


def test_nurse_assessment_string_zero_vitals_are_treated_as_empty(client, db_session, admin_user):
    _, nurse, _, _, patient = _seed_nurse_clinic(db_session, admin_user, salt="-zero")

    r = client.post(
        "/clinical/nurse/assessments",
        headers=_auth(nurse),
        json={
            "patient_id": patient.id,
            "bp_systolic": "0",
            "bp_diastolic": "0",
            "heart_rate": "0",
            "reason_for_consultation": "String zero repro",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["bp_systolic"] is None
    assert body["bp_diastolic"] is None
    assert body["heart_rate"] is None
