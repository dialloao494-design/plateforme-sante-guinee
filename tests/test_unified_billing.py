"""Unified billing — invoice generation and payment."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import models
from security import create_access_token, hash_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
            "session_version": user.session_version,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_unified_invoice_generate_and_pay(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Bill Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"bill.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.flush()
        doctor = models.Doctor(
            user_id=admin_user.id,
            first_name="Bill",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000077",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(reception)
        db_session.refresh(doctor)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Aminata", "last_name": "Camara", "age": 28, "gender": "F"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    search = client.get(
        "/clinical/billing/unified/patients/search",
        params={"q": "Aminata"},
        headers=_auth(reception),
    )
    assert search.status_code == 200
    assert [patient["id"] for patient in search.json()] == [patient_id]

    visits = client.get(
        f"/clinical/billing/unified/patients/{patient_id}/open-visits",
        headers=_auth(reception),
    )
    assert visits.status_code == 200
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
    assert r.status_code == 201, r.text
    invoice = r.json()
    assert invoice["total_amount_gnf"] > 0

    r = client.post(
        f"/clinical/billing/unified/invoices/{invoice['id']}/pay",
        json={"payment_method": "cash"},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"

    r = client.get(
        f"/clinical/billing/unified/invoices/{invoice['id']}/pdf",
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
