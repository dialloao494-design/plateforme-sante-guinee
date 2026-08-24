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
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db.add(reception)
        db.flush()
        doc_user = models.User(
            email=f"hosp.doctor.{suffix}@test.com",
            hashed_password=hash_password("DoctorPass12!"),
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


def test_bed_transfer_sends_previous_bed_to_cleaning(client, db_session, admin_user):
    """A transferred patient's former bed is unavailable until turnover completes."""
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
    assert bed_a.status == "cleaning"
    assert bed_b.status == "occupied"

    r = client.patch(
        f"/clinical/hospitalization/beds/{bed_a_id}",
        json={"status": "available", "reason": "Nettoyage terminé", "expected_version": bed_a.version},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "available"
    assert r.json()["last_cleaned_at"] is not None


def test_ward_board_lifecycle_suitability_and_stale_write(client, db_session, admin_user):
    clinic_id, reception, _doc_user, _doctor = _setup_clinic(client, db_session, admin_user)
    ward = client.post(
        "/clinical/hospitalization/wards",
        json={"code": "PED", "name": "Pédiatrie", "service_type": "pediatric", "location": "Étage 1"},
        headers=_auth(admin_user),
    )
    assert ward.status_code == 201, ward.text
    room = client.post(
        "/clinical/hospitalization/rooms",
        json={"ward_id": ward.json()["id"], "room_number": "P-01", "capacity": 2},
        headers=_auth(admin_user),
    )
    cradle = client.post(
        f"/clinical/hospitalization/rooms/{room.json()['id']}/beds",
        json={"bed_number": "B1", "accommodation_type": "cradle", "newborn_suitable": True},
        headers=_auth(admin_user),
    )
    assert cradle.status_code == 201, cradle.text
    bed = cradle.json()
    assert bed["stable_code"].startswith(f"BED-{clinic_id:03d}-")

    patient = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Bébé", "last_name": "Camara", "age": 0, "gender": "F"},
        headers=_auth(reception),
    )
    admission = client.post(
        "/clinical/hospitalization/admissions",
        json={"patient_id": patient.json()["id"], "placement_age_group": "newborn"},
        headers=_auth(reception),
    )
    assert admission.status_code == 201, admission.text
    reserved = client.post(
        f"/clinical/hospitalization/beds/{bed['id']}/reserve",
        json={
            "admission_id": admission.json()["id"],
            "reserved_until": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "expected_bed_version": bed["version"],
        },
        headers=_auth(reception),
    )
    assert reserved.status_code == 200, reserved.text
    assert reserved.json()["status"] == "reserved"
    bed = reserved.json()
    assigned = client.post(
        f"/clinical/hospitalization/admissions/{admission.json()['id']}/assign-bed",
        json={"bed_id": bed["id"], "expected_bed_version": bed["version"]},
        headers=_auth(reception),
    )
    assert assigned.status_code == 200, assigned.text

    stale = client.patch(
        f"/clinical/hospitalization/beds/{bed['id']}",
        json={"status": "maintenance", "expected_version": bed["version"]},
        headers=_auth(reception),
    )
    assert stale.status_code in (400, 409)

    board = client.get("/clinical/hospitalization/board", headers=_auth(reception))
    assert board.status_code == 200
    ward_data = next(item for item in board.json()["wards"] if item["code"] == "PED")
    bed_data = ward_data["rooms"][0]["beds"][0]
    assert bed_data["status"] == "occupied"
    assert bed_data["patient"]["name"] == "Bébé Camara"
    assert bed_data["newborn_suitable"] is True


def test_cross_clinic_cannot_reserve_or_view_foreign_ward(client, db_session, admin_user):
    _clinic_id, reception, _doc_user, _doctor = _setup_clinic(client, db_session, admin_user)
    room = client.post(
        "/clinical/hospitalization/rooms",
        json={"ward_name": "Isolement", "room_number": "I-1", "capacity": 1},
        headers=_auth(admin_user),
    )
    bed = client.post(
        f"/clinical/hospitalization/rooms/{room.json()['id']}/beds",
        json={"bed_number": "1", "isolation_suitable": True},
        headers=_auth(admin_user),
    ).json()

    suffix = uuid.uuid4().hex[:8]
    other_admin = models.User(email=f"other.ward.{suffix}@test.com", hashed_password=hash_password("OtherPass12!"), role="clinic_admin")
    with provisioning_channel("test_fixture"):
        db_session.add(other_admin)
        db_session.flush()
    other_clinic = models.Clinic(name=f"Other ward clinic {suffix}", city="Conakry")
    db_session.add(other_clinic)
    db_session.flush()
    other_admin.clinic_id = other_clinic.id
    db_session.add(models.ClinicStaff(clinic_id=other_clinic.id, user_id=other_admin.id, is_active=True))
    db_session.commit()

    listed = client.get("/clinical/hospitalization/wards", headers=_auth(other_admin))
    assert listed.status_code == 200
    assert all(item["name"] != "Isolement" for item in listed.json())
    foreign_update = client.patch(
        f"/clinical/hospitalization/beds/{bed['id']}",
        json={"status": "maintenance", "expected_version": bed["version"]},
        headers=_auth(other_admin),
    )
    assert foreign_update.status_code == 404
