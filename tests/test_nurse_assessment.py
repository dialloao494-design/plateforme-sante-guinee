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
        hashed_password=hash_password("NurseTest12!"),
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
            "oxygen_saturation": 98,
            "pain_score": 4,
            "height_cm": 165,
            "weight_kg": 60,
            "arm_circumference_cm": 28.5,
            "head_circumference_cm": 55.0,
            "consciousness_level": "alert",
            "escalation_level": "routine",
            "reason_for_consultation": "Douleur thoracique",
            "allergies": "Aspirine",
            "hospitalized_daily_vitals": "TA 120/80, T 37.8, SpO2 98%",
            "prescription": "Paracétamol 500 mg si douleur",
            "nurse_notes": "Patient anxieux",
            "care_plan": "Recontrôler la douleur dans 30 minutes",
            "handover_sbar": "S: douleur; B: sans allergie; A: stable; R: surveiller",
            "medication_administration": "10:00 Paracétamol 500 mg PO administré",
            "specimen_collection": "Tube EDTA prélevé à 10:10",
            "wound_assessment": "Aucune plaie",
            "safety_checklist": "Risque de chute faible",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reason_for_consultation"] == "Douleur thoracique"
    assert body["bmi"] == 22.0
    assert body["hospitalized_daily_vitals"] == "TA 120/80, T 37.8, SpO2 98%"
    assert body["prescription"] == "Paracétamol 500 mg si douleur"
    assert body["oxygen_saturation"] == 98
    assert body["pain_score"] == 4
    assert body["arm_circumference_cm"] == 28.5
    assert body["head_circumference_cm"] == 55.0
    assert body["care_plan"].startswith("Recontrôler")
    assert body["handover_sbar"].startswith("S: douleur")

    r2 = client.get(
        f"/clinical/nurse/patients/{patient.id}/assessment",
        headers=_auth(nurse),
    )
    assert r2.status_code == 200
    assert r2.json()["allergies"] == "Aspirine"
    assert r2.json()["hospitalized_daily_vitals"] == "TA 120/80, T 37.8, SpO2 98%"

    dq = client.get("/clinical/doctor/queue", headers=_auth(doctor_user))
    assert dq.status_code == 200, dq.text
    assert any(
        item["patient_id"] == patient.id and item.get("source") == "nurse_assessment"
        for item in dq.json()
    )

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


def test_nurse_assessment_creates_distinct_history_rows(client, db_session, admin_user):
    _, nurse, _, _, patient = _seed_nurse_clinic(db_session, admin_user, salt="-history")

    first = client.post(
        "/clinical/nurse/assessments",
        headers=_auth(nurse),
        json={
            "patient_id": patient.id,
            "temperature_c": 37.1,
            "reason_for_consultation": "Première évaluation",
            "allergies": "Arachide",
            "prescription": "Ordonnance première",
        },
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/clinical/nurse/assessments",
        headers=_auth(nurse),
        json={
            "patient_id": patient.id,
            "temperature_c": 38.2,
            "reason_for_consultation": "Deuxième évaluation",
            "allergies": "Latex",
            "prescription": "Ordonnance deuxième",
        },
    )
    assert second.status_code == 201, second.text

    first_body = first.json()
    second_body = second.json()
    assert first_body["id"] != second_body["id"]
    assert first_body["recorded_at"] != second_body["recorded_at"]

    latest = client.get(
        f"/clinical/nurse/patients/{patient.id}/assessment",
        headers=_auth(nurse),
    )
    assert latest.status_code == 200
    assert latest.json()["id"] == second_body["id"]
    assert latest.json()["prescription"] == "Ordonnance deuxième"

    history = client.get(
        f"/clinical/nurse/patients/{patient.id}/assessments",
        headers=_auth(nurse),
    )
    assert history.status_code == 200
    rows = history.json()
    assert [row["id"] for row in rows[:2]] == [second_body["id"], first_body["id"]]
    assert rows[0]["reason_for_consultation"] == "Deuxième évaluation"
    assert rows[1]["reason_for_consultation"] == "Première évaluation"
    assert rows[0]["prescription"] == "Ordonnance deuxième"
    assert rows[1]["prescription"] == "Ordonnance première"


def test_nurse_reads_active_structured_prescriptions_but_not_other_clinic(client, db_session, admin_user):
    clinic_id, nurse, _, doctor, patient = _seed_nurse_clinic(db_session, admin_user, salt="-orders")
    appointment = models.RendezVous(
        clinic_id=clinic_id, patient_id=patient.id, doctor_id=doctor.id,
        date=datetime.utcnow(), status="scheduled", clinical_status="checked_in",
    )
    db_session.add(appointment)
    db_session.flush()
    consultation = models.ClinicalConsultation(
        clinic_id=clinic_id, appointment_id=appointment.id, patient_id=patient.id,
        doctor_id=doctor.id, status="completed",
    )
    db_session.add(consultation)
    db_session.flush()
    prescription = models.Prescription(
        clinic_id=clinic_id, consultation_id=consultation.id, patient_id=patient.id,
        prescriber_doctor_id=doctor.id, status="active",
    )
    db_session.add(prescription)
    db_session.flush()
    db_session.add(models.PrescriptionItem(
        prescription_id=prescription.id, medication_name="Amoxicilline",
        dosage="500 mg", route="oral", frequency="3 fois/jour", duration_days=7,
    ))
    _, _, _, _, foreign_patient = _seed_nurse_clinic(db_session, admin_user, salt="-foreign-orders")
    db_session.commit()

    response = client.get(
        f"/clinical/nurse/patients/{patient.id}/prescriptions", headers=_auth(nurse),
    )
    assert response.status_code == 200, response.text
    assert response.json()[0]["items"][0]["medication_name"] == "Amoxicilline"

    denied = client.get(
        f"/clinical/nurse/patients/{foreign_patient.id}/prescriptions", headers=_auth(nurse),
    )
    assert denied.status_code in (403, 404), denied.text
