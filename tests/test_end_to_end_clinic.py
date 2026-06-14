"""End-to-end clinic workflow — registration through discharge."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import models
from security import create_access_token, hash_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_full_clinic_workflow(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"E2E Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"e2e.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        radtech = models.User(
            email=f"e2e.rad.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="lab_technician",
            clinic_id=clinic_id,
        )
        pharmacist = models.User(
            email=f"e2e.pharma.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="pharmacist",
            clinic_id=clinic_id,
        )
        doc_user = models.User(
            email=f"e2e.doctor.{suffix}@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db_session.add_all([reception, radtech, pharmacist, doc_user])
        db_session.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="E2E",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000444",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(reception)
        db_session.refresh(radtech)
        db_session.refresh(pharmacist)
        db_session.refresh(doc_user)
        db_session.refresh(doctor)

    # Registration
    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Kadiatou", "last_name": "Barry", "age": 29, "gender": "F", "phone": "+224622000444"},
        headers=_auth(reception),
    )
    assert r.status_code == 201
    patient_id = r.json()["id"]

    r = client.get("/clinical/reception/patients", params={"q": "Barry"}, headers=_auth(reception))
    assert r.status_code == 200
    assert any(p["id"] == patient_id for p in r.json())

    # Appointment + reminders
    appt_date = (datetime.now() + timedelta(days=4)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": appt_date.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appt_id = r.json()["id"]
    reminders = db_session.query(models.AppointmentReminder).filter(models.AppointmentReminder.appointment_id == appt_id).count()
    assert reminders == 2

    r = client.post(f"/clinical/reception/appointments/{appt_id}/check-in", headers=_auth(reception))
    assert r.status_code == 200

    # Consultation
    r = client.post("/clinical/consultations", json={"appointment_id": appt_id}, headers=_auth(doc_user))
    consult_id = r.json()["id"]

    r = client.get(f"/patients/{patient_id}/medical-history", headers=_auth(doc_user))
    assert r.status_code == 200

    r = client.post(
        f"/clinical/consultations/{consult_id}/lab-orders",
        json={"test_code": "NFS", "test_name": "NFS", "priority": "routine"},
        headers=_auth(doc_user),
    )
    lab_order_id = r.json()["id"]

    r = client.post(
        f"/clinical/radiology/consultations/{consult_id}/orders",
        json={"modality": "xray", "body_part": "Thorax", "priority": "routine"},
        headers=_auth(doc_user),
    )
    imaging_order_id = r.json()["id"]

    r = client.post(
        f"/clinical/consultations/{consult_id}/prescriptions",
        json={"items": [{"medication_name": "Paracétamol", "dosage": "500mg", "frequency": "3x/j", "duration_days": 5, "route": "oral"}]},
        headers=_auth(doc_user),
    )
    assert r.status_code == 201

    # Lab
    r = client.post(
        f"/clinical/lab/orders/{lab_order_id}/results",
        json={"result_summary": "Normal", "reference_range": "N", "interpretation": "RAS"},
        headers=_auth(radtech),
    )
    lab_result_id = r.json()["id"]
    r = client.post(f"/clinical/lab/results/{lab_result_id}/validate", headers=_auth(radtech))
    assert r.status_code == 200
    r = client.get(f"/clinical/lab/results/{lab_result_id}/pdf", headers=_auth(doc_user))
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"

    # Radiology
    r = client.post(
        f"/clinical/radiology/orders/{imaging_order_id}/report",
        json={"findings": "Normal", "impression": "RAS", "recommendations": None},
        headers=_auth(radtech),
    )
    imaging_result_id = r.json()["id"]
    r = client.post(f"/clinical/radiology/results/{imaging_result_id}/validate", headers=_auth(doc_user))
    assert r.status_code == 200

    # Pharmacy
    r = client.get("/clinical/pharmacy/orders", headers=_auth(pharmacist))
    pharma_order = r.json()[0]
    r = client.patch(f"/clinical/pharmacy/orders/{pharma_order['id']}", json={"status": "dispensed"}, headers=_auth(pharmacist))
    assert r.status_code == 200

    # Billing
    r = client.post(
        "/clinical/billing/unified/invoices/generate",
        json={"patient_id": patient_id},
        headers=_auth(reception),
    )
    invoice = r.json()
    visit_id = invoice["visit_id"]
    r = client.post(
        f"/clinical/billing/unified/invoices/{invoice['id']}/pay",
        json={"payment_method": "orange_money"},
        headers=_auth(reception),
    )
    assert r.status_code == 200

    # Reporting
    r = client.get("/clinical/reports/summary", headers=_auth(reception))
    assert r.status_code == 200
    r = client.get("/clinical/reports/export.pdf", headers=_auth(reception))
    assert r.status_code == 200

    # Discharge
    r = client.get(f"/clinical/discharge/checklist/{visit_id}", headers=_auth(reception))
    assert r.json()["ready_for_discharge"] is True
    r = client.post(
        "/clinical/discharge/execute",
        json={"visit_id": visit_id, "follow_up_instructions": "Contrôle 7j"},
        headers=_auth(reception),
    )
    assert r.status_code == 201
    assert r.json()["archived_to_emr"] is True

    # WhatsApp patient response
    r = client.post(
        f"/clinical/reminders/appointments/{appt_id}/respond",
        json={"action": "reschedule_requested", "payload": "REPORTER"},
    )
    assert r.status_code == 200
    appt = db_session.query(models.RendezVous).filter(models.RendezVous.id == appt_id).first()
    assert appt.clinical_status == "reschedule_requested"
