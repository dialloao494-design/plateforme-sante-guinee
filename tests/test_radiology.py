"""Radiology module — imaging orders, reports, EMR attachment, billing."""

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


def _clinical_setup(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Rad Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"rad.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        radtech = models.User(
            email=f"rad.tech.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="lab_technician",
            clinic_id=clinic_id,
        )
        db_session.add_all([reception, radtech])
        db_session.flush()
        doc_user = models.User(
            email=f"rad.doctor.{suffix}@test.com",
            hashed_password=hash_password("DoctorPass12!"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db_session.add(doc_user)
        db_session.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="Rad",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000111",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(reception)
        db_session.refresh(radtech)
        db_session.refresh(doc_user)
        db_session.refresh(doctor)
    return clinic_id, reception, radtech, doc_user, doctor


def test_radiology_order_report_validate_and_emr(client, db_session, admin_user):
    _clinic_id, reception, radtech, doc_user, doctor = _clinical_setup(client, db_session, admin_user)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Ibrahima", "last_name": "Sylla", "age": 40, "gender": "M", "phone": "+224622000111"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=2)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appt_id = r.json()["id"]
    r = client.post(f"/clinical/reception/appointments/{appt_id}/check-in", headers=_auth(reception))
    assert r.status_code == 200

    r = client.post(
        "/clinical/consultations",
        json={"appointment_id": appt_id},
        headers=_auth(doc_user),
    )
    assert r.status_code == 201, r.text
    consultation_id = r.json()["id"]

    r = client.post(
        f"/clinical/radiology/consultations/{consultation_id}/orders",
        json={
            "modality": "xray",
            "body_part": "Thorax",
            "clinical_indication": "Toux persistante",
            "priority": "routine",
        },
        headers=_auth(doc_user),
    )
    assert r.status_code == 201, r.text
    order_id = r.json()["id"]

    r = client.get("/clinical/radiology/orders", headers=_auth(radtech))
    assert r.status_code == 200
    assert any(o["id"] == order_id for o in r.json())

    r = client.patch(
        f"/clinical/radiology/orders/{order_id}",
        json={"status": "scheduled"},
        headers=_auth(radtech),
    )
    assert r.status_code == 200

    r = client.post(
        f"/clinical/radiology/orders/{order_id}/report",
        json={
            "findings": "Opacité basale droite",
            "impression": "Pneumonie probable",
            "recommendations": "Antibiothérapie et contrôle",
        },
        headers=_auth(radtech),
    )
    assert r.status_code == 201, r.text
    result_id = r.json()["id"]

    r = client.post(f"/clinical/radiology/results/{result_id}/validate", headers=_auth(doc_user))
    assert r.status_code == 200

    docs = (
        db_session.query(models.PatientDocument)
        .filter(models.PatientDocument.patient_id == patient_id, models.PatientDocument.type_document == "imaging_report")
        .all()
    )
    assert len(docs) >= 1

    charges = (
        db_session.query(models.ClinicCharge)
        .filter(
            models.ClinicCharge.patient_id == patient_id,
            models.ClinicCharge.charge_type == "radiology",
        )
        .all()
    )
    assert len(charges) >= 1
