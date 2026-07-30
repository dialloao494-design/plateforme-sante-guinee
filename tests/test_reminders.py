"""WhatsApp appointment reminders and staff notification center."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import models
from core.provisioning_context import provisioning_channel
from core.reminder_security import expected_reminder_respond_token
from security import create_access_token, hash_password


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def _respond_payload(appointment_id: int, action: str) -> dict:
    return {
        "action": action,
        "token": expected_reminder_respond_token(appointment_id),
    }

def test_reminder_scheduling_and_patient_response(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Rem Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"rem.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.flush()
        doctor = models.Doctor(
            user_id=admin_user.id,
            first_name="Rem",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000222",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(reception)
        db_session.refresh(doctor)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Mariama", "last_name": "Diallo", "age": 32, "gender": "F", "phone": "+224622000222"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    appt_date = (datetime.now() + timedelta(days=3)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": appt_date.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    assert r.status_code == 201, r.text
    appt_id = r.json()["id"]

    reminders = (
        db_session.query(models.AppointmentReminder)
        .filter(models.AppointmentReminder.appointment_id == appt_id)
        .all()
    )
    assert len(reminders) == 2
    assert {r.reminder_type for r in reminders} == {"48h", "24h"}

    r = client.post(
        f"/clinical/reminders/appointments/{appt_id}/respond",
        json=_respond_payload(appt_id, "confirmed"),
    )
    assert r.status_code == 200

    r = client.get("/clinical/reminders/notifications", headers=_auth(reception))
    assert r.status_code == 200
    assert any(n["event_type"] == "confirmed" for n in r.json())

    r = client.post(
        f"/clinical/reminders/appointments/{appt_id}/respond",
        json=_respond_payload(appt_id, "cancelled"),
    )
    assert r.status_code == 200
    appt = db_session.query(models.RendezVous).filter(models.RendezVous.id == appt_id).first()
    assert appt.status == "cancelled"


def test_reschedule_requested_notification(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Resched Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"res.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.flush()
        doctor = models.Doctor(
            user_id=admin_user.id,
            first_name="Res",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000333",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(reception)
        db_session.refresh(doctor)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Aissatou", "last_name": "Keita", "age": 25, "gender": "F", "phone": "+224622000333"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    appt_date = (datetime.now() + timedelta(days=5)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": appt_date.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appt_id = r.json()["id"]
    r = client.post(
        f"/clinical/reminders/appointments/{appt_id}/respond",
        json=_respond_payload(appt_id, "reschedule_requested"),
    )
    assert r.status_code == 200
    r = client.get("/clinical/reminders/notifications", headers=_auth(reception))
    assert any(n["event_type"] == "reschedule_requested" for n in r.json())
