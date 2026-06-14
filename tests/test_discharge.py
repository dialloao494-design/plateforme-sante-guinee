"""Patient discharge — checklist, billing validation, EMR archive, PDF."""

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


def _setup_clinic(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Discharge Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    assert r.status_code == 201, r.text
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"dis.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.flush()
        doctor = models.Doctor(
            user_id=admin_user.id,
            first_name="Dis",
            last_name="Doc",
            specialty="MG",
            city="Conakry",
            phone="+224600000099",
            clinic_id=clinic_id,
            consultation_fee=150_000,
        )
        db_session.add(doctor)
        db_session.commit()
        db_session.refresh(reception)
        db_session.refresh(doctor)
    return clinic_id, reception, doctor


def test_discharge_workflow_with_billing_and_emr(client, db_session, admin_user):
    _clinic_id, reception, doctor = _setup_clinic(client, db_session, admin_user)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Fatoumata", "last_name": "Bah", "age": 35, "gender": "F"},
        headers=_auth(reception),
    )
    assert r.status_code == 201
    patient_id = r.json()["id"]

    slot = (datetime.now() + timedelta(hours=4)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor.id,
            "date": slot.isoformat(),
            "duration_minutes": 30,
        },
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
    visit_id = invoice["visit_id"]
    assert visit_id is not None

    r = client.get(f"/clinical/discharge/checklist/{visit_id}", headers=_auth(reception))
    assert r.status_code == 200
    checklist = r.json()
    assert checklist["invoice_validated"] is False
    assert checklist["ready_for_discharge"] is False

    r = client.post(
        f"/clinical/billing/unified/invoices/{invoice['id']}/pay",
        json={"payment_method": "cash"},
        headers=_auth(reception),
    )
    assert r.status_code == 200

    r = client.get(f"/clinical/discharge/checklist/{visit_id}", headers=_auth(reception))
    checklist = r.json()
    assert checklist["invoice_validated"] is True
    assert checklist["ready_for_discharge"] is True

    r = client.get("/clinical/discharge/visits/open", headers=_auth(reception))
    assert r.status_code == 200
    assert any(v["id"] == visit_id for v in r.json())

    r = client.post(
        "/clinical/discharge/execute",
        json={"visit_id": visit_id, "follow_up_instructions": "Contrôle dans 7 jours"},
        headers=_auth(reception),
    )
    assert r.status_code == 201, r.text
    summary = r.json()
    assert summary["archived_to_emr"] is True
    assert summary["invoice_validated"] is True
    assert summary["follow_up_instructions"] == "Contrôle dans 7 jours"

    r = client.get(f"/clinical/discharge/summaries/{summary['id']}/pdf", headers=_auth(reception))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"

    notes = (
        db_session.query(models.ClinicalNote)
        .filter(models.ClinicalNote.patient_id == patient_id, models.ClinicalNote.note_type == "discharge")
        .all()
    )
    assert len(notes) >= 1
