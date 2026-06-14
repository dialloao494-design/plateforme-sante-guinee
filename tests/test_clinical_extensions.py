"""Integration tests for new clinical modules."""

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


def _setup(client, db, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Ext Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"ext.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db.add(reception)
        db.flush()
        doc_user = models.User(
            email=f"ext.doctor.{suffix}@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db.add(doc_user)
        db.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="Ext",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000033",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db.add(doctor)
        db.commit()
        db.refresh(reception)
        db.refresh(doctor)
    return clinic_id, reception, doctor


def test_hospitalization_room_and_occupancy(client, db_session, admin_user):
    clinic_id, reception, _doctor = _setup(client, db_session, admin_user)
    r = client.post(
        "/clinical/hospitalization/rooms",
        json={"ward_name": "Médecine", "room_number": "501", "capacity": 2},
        headers=_auth(admin_user),
    )
    assert r.status_code == 201
    room_id = r.json()["id"]
    r = client.post(
        f"/clinical/hospitalization/rooms/{room_id}/beds",
        json={"bed_number": "A"},
        headers=_auth(admin_user),
    )
    assert r.status_code == 201
    r = client.get("/clinical/hospitalization/occupancy", headers=_auth(reception))
    assert r.status_code == 200
    assert r.json()["total_beds"] >= 1


def test_unified_billing_invoice_flow(client, db_session, admin_user):
    clinic_id, reception, doctor = _setup(client, db_session, admin_user)
    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Aminata", "last_name": "Camara", "age": 28, "gender": "F"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=4)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    assert r.status_code == 201
    r = client.post(
        "/clinical/billing/unified/invoices/generate",
        json={"patient_id": patient_id},
        headers=_auth(reception),
    )
    assert r.status_code == 201
    invoice = r.json()
    assert invoice["total_amount_gnf"] > 0
    r = client.post(
        f"/clinical/billing/unified/invoices/{invoice['id']}/pay",
        json={"payment_method": "cash"},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


def test_radiology_order_endpoint(client, db_session, admin_user):
    clinic_id, reception, doctor = _setup(client, db_session, admin_user)
    with provisioning_channel("test_fixture"):
        lab_user = models.User(
            email=f"ext.lab.{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="lab_technician",
            clinic_id=clinic_id,
        )
        db_session.add(lab_user)
        db_session.commit()
        db_session.refresh(lab_user)
    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Ibrahima", "last_name": "Bah", "age": 40, "gender": "M"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=5)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appt_id = r.json()["id"]
    client.post(f"/clinical/reception/appointments/{appt_id}/check-in", headers=_auth(reception))
    doc_user = db_session.query(models.User).filter(models.User.id == doctor.user_id).first()
    r = client.post(
        "/clinical/consultations",
        json={"appointment_id": appt_id, "chief_complaint": "Douleur thoracique"},
        headers=_auth(doc_user),
    )
    consult_id = r.json()["id"]
    r = client.post(
        f"/clinical/radiology/consultations/{consult_id}/orders",
        json={"modality": "xray", "body_part": "Thorax", "priority": "routine"},
        headers=_auth(doc_user),
    )
    assert r.status_code == 201
    r = client.get("/clinical/radiology/orders", headers=_auth(lab_user))
    assert r.status_code == 200
    assert len(r.json()) >= 1
