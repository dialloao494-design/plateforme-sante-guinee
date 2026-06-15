"""Hospitalization module — rooms, beds, admissions, transfers."""

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


def _setup_clinic(client, db, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Hosp Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    assert r.status_code == 201, r.text
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"hosp.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db.add(reception)
        db.flush()
        doc_user = models.User(
            email=f"hosp.doctor.{suffix}@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db.add(doc_user)
        db.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="Hosp",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000088",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db.add(doctor)
        db.commit()
        db.refresh(reception)
        db.refresh(doctor)
        db.refresh(doc_user)
    return clinic_id, reception, doc_user, doctor


def test_hospitalization_room_bed_occupancy(client, db_session, admin_user):
    _clinic_id, reception, _doc_user, _doctor = _setup_clinic(client, db_session, admin_user)
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
    data = r.json()
    assert data["total_beds"] >= 1
    assert data["available_beds"] >= 1


def test_admit_from_consultation_and_assign_bed(client, db_session, admin_user):
    clinic_id, reception, doc_user, doctor = _setup_clinic(client, db_session, admin_user)
    r = client.post(
        "/clinical/hospitalization/rooms",
        json={"ward_name": "Chirurgie", "room_number": "201", "capacity": 1},
        headers=_auth(admin_user),
    )
    room_id = r.json()["id"]
    r = client.post(
        f"/clinical/hospitalization/rooms/{room_id}/beds",
        json={"bed_number": "1"},
        headers=_auth(admin_user),
    )
    bed_id = r.json()["id"]

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Mariama", "last_name": "Diallo", "age": 32, "gender": "F"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=6)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appt_id = r.json()["id"]
    client.post(f"/clinical/reception/appointments/{appt_id}/check-in", headers=_auth(reception))
    r = client.post(
        "/clinical/consultations",
        json={"appointment_id": appt_id, "chief_complaint": "Douleur abdominale"},
        headers=_auth(doc_user),
    )
    consult_id = r.json()["id"]
    r = client.post(
        "/clinical/hospitalization/admissions",
        json={"consultation_id": consult_id, "reason": "Observation 24h"},
        headers=_auth(doc_user),
    )
    assert r.status_code == 201
    admission_id = r.json()["id"]
    assert r.json()["status"] == "pending"

    r = client.post(
        f"/clinical/hospitalization/admissions/{admission_id}/assign-bed",
        json={"bed_id": bed_id},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "admitted"
    assert r.json()["current_bed"]["bed_number"] == "1"

    r = client.get("/clinical/hospitalization/occupancy", headers=_auth(reception))
    assert r.json()["occupied_beds"] >= 1

    r = client.patch(
        f"/clinical/hospitalization/admissions/{admission_id}/status",
        json={"status": "in_care"},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_care"


def test_bed_transfer_releases_previous_bed(client, db_session, admin_user):
    """Assign bed A then bed B — admission status transferred, bed A available."""
    clinic_id, reception, doc_user, doctor = _setup_clinic(client, db_session, admin_user)

    r = client.post(
        "/clinical/hospitalization/rooms",
        json={"ward_name": "Transfert", "room_number": "T101", "capacity": 2},
        headers=_auth(admin_user),
    )
    room_a_id = r.json()["id"]
    r = client.post(
        f"/clinical/hospitalization/rooms/{room_a_id}/beds",
        json={"bed_number": "A1"},
        headers=_auth(admin_user),
    )
    bed_a_id = r.json()["id"]

    r = client.post(
        "/clinical/hospitalization/rooms",
        json={"ward_name": "Transfert", "room_number": "T102", "capacity": 1},
        headers=_auth(admin_user),
    )
    room_b_id = r.json()["id"]
    r = client.post(
        f"/clinical/hospitalization/rooms/{room_b_id}/beds",
        json={"bed_number": "B1"},
        headers=_auth(admin_user),
    )
    bed_b_id = r.json()["id"]

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Transfer", "last_name": "Patient", "age": 45, "gender": "M"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=7)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appt_id = r.json()["id"]
    client.post(f"/clinical/reception/appointments/{appt_id}/check-in", headers=_auth(reception))
    r = client.post(
        "/clinical/consultations",
        json={"appointment_id": appt_id, "chief_complaint": "Transfert lit"},
        headers=_auth(doc_user),
    )
    consult_id = r.json()["id"]
    r = client.post(
        "/clinical/hospitalization/admissions",
        json={"consultation_id": consult_id, "reason": "Observation"},
        headers=_auth(doc_user),
    )
    admission_id = r.json()["id"]

    r = client.post(
        f"/clinical/hospitalization/admissions/{admission_id}/assign-bed",
        json={"bed_id": bed_a_id},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "admitted"
    assert r.json()["current_bed"]["bed_number"] == "A1"

    r = client.post(
        f"/clinical/hospitalization/admissions/{admission_id}/assign-bed",
        json={"bed_id": bed_b_id, "transfer_reason": "Besoin chambre individuelle"},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "transferred"
    assert body["current_bed"]["bed_number"] == "B1"
    assert len(body["stays"]) == 2
    assert sum(1 for s in body["stays"] if s["is_current"]) == 1

    bed_a = db_session.query(models.HospitalBed).filter(models.HospitalBed.id == bed_a_id).first()
    bed_b = db_session.query(models.HospitalBed).filter(models.HospitalBed.id == bed_b_id).first()
    assert bed_a.status == "available"
    assert bed_b.status == "occupied"
