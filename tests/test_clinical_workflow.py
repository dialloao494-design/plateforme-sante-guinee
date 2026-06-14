"""End-to-end clinical workflow: patient → appointment → consultation → lab → pharmacy."""

from __future__ import annotations

from datetime import datetime, timedelta

import models
from core.provisioning_context import provisioning_channel
from security import hash_password, create_access_token


def _auth_header(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _staff(db, email, role, clinic_id, password="StaffPass1"):
    with provisioning_channel("test_fixture"):
        user = models.User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            clinic_id=clinic_id,
        )
        db.add(user)
        db.add(models.ClinicStaff(clinic_id=clinic_id, user_id=0, is_active=True))
        db.flush()
        db.query(models.ClinicStaff).filter(models.ClinicStaff.user_id == 0).update(
            {"user_id": user.id}
        )
        db.commit()
        db.refresh(user)
    return user


def test_full_clinical_workflow(client, db_session, admin_user):
    # Admin creates clinic
    r = client.post(
        "/clinical/clinics",
        json={"name": "Clinique Démo CIS", "city": "Conakry"},
        headers=_auth_header(admin_user),
    )
    assert r.status_code == 201
    clinic_id = r.json()["id"]

    # Doctor profile + staff
    with provisioning_channel("test_fixture"):
        doc_user = models.User(
            email="doctor.cis@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db_session.add(doc_user)
        db_session.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="Alpha",
            last_name="Diallo",
            specialty="Médecine générale",
            city="Conakry",
            phone="+224600000001",
            clinic_id=clinic_id,
        )
        db_session.add(doctor)
        db_session.add(
            models.DoctorAvailability(
                doctor_id=0,
                day_of_week=datetime.utcnow().weekday(),
                start_time=datetime.strptime("08:00", "%H:%M").time(),
                end_time=datetime.strptime("20:00", "%H:%M").time(),
                is_active=True,
            )
        )
        db_session.flush()
        db_session.query(models.DoctorAvailability).filter(
            models.DoctorAvailability.doctor_id == 0
        ).update({"doctor_id": doctor.id})
        db_session.commit()
        db_session.refresh(doctor)

    reception = _staff(db_session, "reception.cis@test.com", "receptionist", clinic_id)
    lab_tech = _staff(db_session, "lab.cis@test.com", "lab_technician", clinic_id)
    pharmacist = _staff(db_session, "pharmacy.cis@test.com", "pharmacist", clinic_id)

    # Reception: register patient
    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Mariama", "last_name": "Camara", "age": 28, "gender": "F"},
        headers=_auth_header(reception),
    )
    assert r.status_code == 201
    patient_id = r.json()["id"]

    slot = (datetime.now() + timedelta(hours=2)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor.id,
            "date": slot.isoformat(),
            "duration_minutes": 30,
        },
        headers=_auth_header(reception),
    )
    assert r.status_code == 201, r.text
    appointment_id = r.json()["id"]

    r = client.post(
        f"/clinical/reception/appointments/{appointment_id}/check-in",
        headers=_auth_header(reception),
    )
    assert r.status_code == 200
    assert r.json()["clinical_status"] == "checked_in"

    # Doctor: consultation + lab + prescription
    r = client.post(
        "/clinical/consultations",
        json={"appointment_id": appointment_id, "chief_complaint": "Fièvre"},
        headers=_auth_header(doc_user),
    )
    assert r.status_code == 201
    consultation_id = r.json()["id"]

    r = client.post(
        f"/clinical/consultations/{consultation_id}/lab-orders",
        json={"test_code": "CRP", "test_name": "Protéine C réactive"},
        headers=_auth_header(doc_user),
    )
    assert r.status_code == 201
    lab_order_id = r.json()["id"]

    r = client.post(
        f"/clinical/consultations/{consultation_id}/prescriptions",
        json={
            "items": [
                {
                    "medication_name": "Paracétamol",
                    "dosage": "500mg",
                    "frequency": "3x/jour",
                    "duration_days": 5,
                }
            ]
        },
        headers=_auth_header(doc_user),
    )
    assert r.status_code == 201

    # Lab: result
    r = client.post(
        f"/clinical/lab/orders/{lab_order_id}/results",
        json={"result_summary": "CRP 12 mg/L", "reference_range": "< 5 mg/L"},
        headers=_auth_header(lab_tech),
    )
    assert r.status_code == 201
    result_id = r.json()["id"]
    r = client.post(f"/clinical/lab/results/{result_id}/validate", headers=_auth_header(lab_tech))
    assert r.status_code == 200

    # Pharmacy: dispense
    r = client.get("/clinical/pharmacy/orders", headers=_auth_header(pharmacist))
    assert r.status_code == 200
    assert len(r.json()) >= 1
    pharmacy_order_id = r.json()[0]["id"]
    r = client.patch(
        f"/clinical/pharmacy/orders/{pharmacy_order_id}",
        json={"status": "dispensed"},
        headers=_auth_header(pharmacist),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "dispensed"

    journey = client.get(
        f"/clinical/patients/{patient_id}/journey",
        headers=_auth_header(reception),
    )
    assert journey.status_code == 200
    assert len(journey.json()["appointments"]) >= 1


def test_resume_active_consultation(client, db_session, admin_user):
    """Doctor can resume when appointment is already in_consultation."""
    r = client.post(
        "/clinical/clinics",
        json={"name": "Clinique Reprise", "city": "Conakry"},
        headers=_auth_header(admin_user),
    )
    assert r.status_code == 201
    clinic_id = r.json()["id"]

    with provisioning_channel("test_fixture"):
        doc_user = models.User(
            email="doctor.resume@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db_session.add(doc_user)
        db_session.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="Resume",
            last_name="Doc",
            specialty="Médecine générale",
            city="Conakry",
            phone="+224600000002",
            clinic_id=clinic_id,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(doctor)

    reception = _staff(db_session, "reception.resume@test.com", "receptionist", clinic_id)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Aissatou", "last_name": "Bah", "age": 22, "gender": "F"},
        headers=_auth_header(reception),
    )
    patient_id = r.json()["id"]

    slot = (datetime.now() + timedelta(hours=1)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor.id,
            "date": slot.isoformat(),
            "duration_minutes": 30,
        },
        headers=_auth_header(reception),
    )
    appointment_id = r.json()["id"]
    client.post(
        f"/clinical/reception/appointments/{appointment_id}/check-in",
        headers=_auth_header(reception),
    )

    r1 = client.post(
        "/clinical/consultations",
        json={"appointment_id": appointment_id},
        headers=_auth_header(doc_user),
    )
    assert r1.status_code == 201
    consultation_id = r1.json()["id"]

    r2 = client.post(
        "/clinical/consultations",
        json={"appointment_id": appointment_id},
        headers=_auth_header(doc_user),
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == consultation_id


def test_admin_create_doctor_profile(client, db_session, admin_user):
    r = client.post(
        "/clinical/clinics",
        json={"name": "Clinique Staff", "city": "Conakry"},
        headers=_auth_header(admin_user),
    )
    clinic_id = r.json()["id"]

    r = client.post(
        "/clinical/staff",
        json={
            "email": "new.doctor@test.com",
            "password": "DoctorNew1!",
            "role": "doctor",
            "clinic_id": clinic_id,
        },
        headers=_auth_header(admin_user),
    )
    assert r.status_code == 201, r.text
    doc = (
        db_session.query(models.Doctor)
        .join(models.User, models.Doctor.user_id == models.User.id)
        .filter(models.User.email == "new.doctor@test.com")
        .first()
    )
    assert doc is not None
    assert doc.clinic_id == clinic_id

    login = client.post(
        "/auth/login-json",
        json={"email": "new.doctor@test.com", "password": "DoctorNew1!"},
    )
    assert login.status_code == 200


def test_assign_doctor_syncs_user_clinic(client, db_session, admin_user):
    r = client.post(
        "/clinical/clinics",
        json={"name": "Clinique A", "city": "Conakry"},
        headers=_auth_header(admin_user),
    )
    clinic_a = r.json()["id"]
    r = client.post(
        "/clinical/clinics",
        json={"name": "Clinique B", "city": "Kindia"},
        headers=_auth_header(admin_user),
    )
    clinic_b = r.json()["id"]

    with provisioning_channel("test_fixture"):
        doc_user = models.User(
            email="doctor.assign@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_a,
        )
        db_session.add(doc_user)
        db_session.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="Assign",
            last_name="Test",
            specialty="Médecine générale",
            city="Conakry",
            phone="+224600000003",
            clinic_id=clinic_a,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(doctor)

    r = client.patch(
        f"/clinical/doctors/{doctor.id}/clinic/{clinic_b}",
        headers=_auth_header(admin_user),
    )
    assert r.status_code == 204

    db_session.refresh(doc_user)
    db_session.refresh(doctor)
    assert doctor.clinic_id == clinic_b
    assert doc_user.clinic_id == clinic_b


def test_lab_staff_login_after_admin_create(client, admin_user):
    r = client.post(
        "/clinical/clinics",
        json={"name": "Clinique Labo", "city": "Conakry"},
        headers=_auth_header(admin_user),
    )
    clinic_id = r.json()["id"]

    r = client.post(
        "/clinical/staff",
        json={
            "email": "lab.outbox@test.com",
            "password": "LabOutBox1!",
            "role": "lab_technician",
            "clinic_id": clinic_id,
        },
        headers=_auth_header(admin_user),
    )
    assert r.status_code == 201, r.text

    login = client.post(
        "/auth/login-json",
        json={"email": "lab.outbox@test.com", "password": "LabOutBox1!"},
    )
    assert login.status_code == 200
    assert login.json()["role"] == "lab_technician"
