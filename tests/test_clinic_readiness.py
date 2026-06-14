"""Real clinic readiness — audit, billing, timeline, backup."""

from __future__ import annotations

import gzip
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import models
from models.clinical_audit_log import ClinicalAuditLog
from security import create_access_token, hash_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def _staff(db, email, role, clinic_id):
    with provisioning_channel("test_fixture"):
        user = models.User(
            email=email,
            hashed_password=hash_password("StaffPass1"),
            role=role,
            clinic_id=clinic_id,
        )
        db.add(user)
        db.add(models.ClinicStaff(clinic_id=clinic_id, user_id=0, is_active=True))
        db.flush()
        db.query(models.ClinicStaff).filter(models.ClinicStaff.user_id == 0).update({"user_id": user.id})
        db.commit()
        db.refresh(user)
    return user


def _setup_clinic(client, db, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Clinique Readiness {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    db.commit()
    db.refresh(admin_user)
    reception = _staff(db, f"readiness.reception.{suffix}@test.com", "receptionist", clinic_id)
    cashier = _staff(db, f"readiness.cashier.{suffix}@test.com", "cashier", clinic_id)
    with provisioning_channel("test_fixture"):
        doc_user = models.User(
            email=f"readiness.doctor.{suffix}@test.com",
            hashed_password=hash_password("DoctorPass1"),
            role="doctor",
            clinic_id=clinic_id,
        )
        db.add(doc_user)
        db.flush()
        doctor = models.Doctor(
            user_id=doc_user.id,
            first_name="Readiness",
            last_name="Doc",
            specialty="Médecine générale",
            city="Conakry",
            phone="+224600000099",
            clinic_id=clinic_id,
            consultation_fee=200_000,
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
    return clinic_id, reception, cashier, doc_user, doctor


def test_cis_actions_create_audit_logs(client, db_session, admin_user):
    clinic_id, reception, cashier, doc_user, doctor = _setup_clinic(client, db_session, admin_user)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Fatou", "last_name": "Sylla", "age": 35, "gender": "F"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]

    slot = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appointment_id = r.json()["id"]

    before = db_session.query(ClinicalAuditLog).filter(ClinicalAuditLog.clinic_id == clinic_id).count()
    client.post(f"/clinical/reception/appointments/{appointment_id}/check-in", headers=_auth(reception))
    after = db_session.query(ClinicalAuditLog).filter(ClinicalAuditLog.clinic_id == clinic_id).count()
    assert after > before

    logs = client.get("/clinical/audit-logs", headers=_auth(admin_user))
    assert logs.status_code == 200
    assert len(logs.json()) >= 1


def test_denied_access_logged(client, db_session, admin_user):
    clinic_id, reception, cashier, doc_user, doctor = _setup_clinic(client, db_session, admin_user)
    lab = _staff(db_session, f"readiness.lab.{uuid.uuid4().hex[:8]}@test.com", "lab_technician", clinic_id)
    before = db_session.query(ClinicalAuditLog).filter(ClinicalAuditLog.action.like("denied_%")).count()
    r = client.get("/clinical/billing/revenue/daily", headers=_auth(lab))
    assert r.status_code == 403
    after = db_session.query(ClinicalAuditLog).filter(ClinicalAuditLog.action.like("denied_%")).count()
    assert after > before


def test_unified_timeline_includes_cis(client, db_session, admin_user):
    clinic_id, reception, cashier, doc_user, doctor = _setup_clinic(client, db_session, admin_user)
    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Timeline", "last_name": "Test", "age": 40, "gender": "M"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=4)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appointment_id = r.json()["id"]
    client.post(f"/clinical/reception/appointments/{appointment_id}/check-in", headers=_auth(reception))
    r = client.post(
        "/clinical/consultations",
        json={"appointment_id": appointment_id, "chief_complaint": "Céphalées"},
        headers=_auth(doc_user),
    )
    consultation_id = r.json()["id"]
    client.post(
        f"/clinical/consultations/{consultation_id}/lab-orders",
        json={"test_code": "GLU", "test_name": "Glycémie"},
        headers=_auth(doc_user),
    )

    timeline = client.get(f"/patients/{patient_id}/timeline", headers=_auth(doc_user))
    assert timeline.status_code == 200
    types = {e["event_type"] for e in timeline.json()}
    assert "cis_consultation" in types
    assert "lab_order" in types
    assert "billing_charge" in types


def test_billing_consultation_lab_pharmacy(client, db_session, admin_user):
    clinic_id, reception, cashier, doc_user, doctor = _setup_clinic(client, db_session, admin_user)
    lab = _staff(db_session, f"readiness.lab2.{uuid.uuid4().hex[:8]}@test.com", "lab_technician", clinic_id)
    pharmacist = _staff(db_session, f"readiness.pharma.{uuid.uuid4().hex[:8]}@test.com", "pharmacist", clinic_id)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Billing", "last_name": "Patient", "age": 50, "gender": "M"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=5)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appointment_id = r.json()["id"]
    client.post(f"/clinical/reception/appointments/{appointment_id}/check-in", headers=_auth(reception))
    r = client.post("/clinical/consultations", json={"appointment_id": appointment_id}, headers=_auth(doc_user))
    consultation_id = r.json()["id"]
    client.post(
        f"/clinical/consultations/{consultation_id}/lab-orders",
        json={"test_code": "NFS", "test_name": "NFS"},
        headers=_auth(doc_user),
    )
    client.post(
        f"/clinical/consultations/{consultation_id}/prescriptions",
        json={"items": [{"medication_name": "Amoxicilline", "dosage": "500mg", "frequency": "2x/jour", "duration_days": 7}]},
        headers=_auth(doc_user),
    )

    pending = client.get("/clinical/billing/charges/pending", headers=_auth(reception))
    assert pending.status_code == 200
    charges = pending.json()
    assert len(charges) >= 3
    types = {c["charge_type"] for c in charges}
    assert types >= {"consultation", "laboratory", "pharmacy"}

    for charge in charges:
        pay = client.post(
            f"/clinical/billing/charges/{charge['id']}/pay",
            json={"payment_method": "cash"},
            headers=_auth(cashier),
        )
        assert pay.status_code == 200
        assert pay.json()["payment_status"] == "paid"

    revenue = client.get("/clinical/billing/revenue/daily", headers=_auth(admin_user))
    assert revenue.status_code == 200
    assert revenue.json()["total_collected_gnf"] > 0
    assert revenue.json()["paid_count"] >= 3


def test_backup_validation_service(tmp_path):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    backup_file = backup_dir / "sante_test.sql.gz"
    with gzip.open(backup_file, "wt", encoding="utf-8") as fh:
        fh.write("-- PostgreSQL database dump\nSELECT 1;\n")

    from services.backup_validation_service import validate_backup_directory

    result = validate_backup_directory(backup_dir, max_age_hours=26)
    assert result["status"] == "ok"
    assert result["gzip_valid"] is True

    admin_token = None
    assert result["latest_backup"] == "sante_test.sql.gz"


def test_lab_validation_creates_document(client, db_session, admin_user):
    clinic_id, reception, cashier, doc_user, doctor = _setup_clinic(client, db_session, admin_user)
    lab = _staff(db_session, f"readiness.lab3.{uuid.uuid4().hex[:8]}@test.com", "lab_technician", clinic_id)

    r = client.post(
        "/clinical/reception/patients",
        json={"first_name": "Doc", "last_name": "Lab", "age": 33, "gender": "F"},
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]
    slot = (datetime.now() + timedelta(hours=6)).replace(second=0, microsecond=0)
    r = client.post(
        "/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor.id, "date": slot.isoformat(), "duration_minutes": 30},
        headers=_auth(reception),
    )
    appointment_id = r.json()["id"]
    client.post(f"/clinical/reception/appointments/{appointment_id}/check-in", headers=_auth(reception))
    r = client.post("/clinical/consultations", json={"appointment_id": appointment_id}, headers=_auth(doc_user))
    consultation_id = r.json()["id"]
    r = client.post(
        f"/clinical/consultations/{consultation_id}/lab-orders",
        json={"test_code": "CRP", "test_name": "CRP"},
        headers=_auth(doc_user),
    )
    lab_order_id = r.json()["id"]
    r = client.post(
        f"/clinical/lab/orders/{lab_order_id}/results",
        json={"result_summary": "CRP 8 mg/L", "reference_range": "< 5"},
        headers=_auth(lab),
    )
    result_id = r.json()["id"]
    client.post(f"/clinical/lab/results/{result_id}/validate", headers=_auth(lab))

    docs = client.get(f"/patients/{patient_id}/documents", headers=_auth(doc_user))
    assert docs.status_code == 200
    assert any(d["type_document"] == "lab_result" for d in docs.json())
