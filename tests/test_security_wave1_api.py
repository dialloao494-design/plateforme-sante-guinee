"""Security Wave 1 — API / FastAPI / IDOR / validation tests."""

from __future__ import annotations

import models
from core.authorize import authorize
from core.input_validation import reject_suspicious_sql_input
from core.output_encoding import escape_html, escape_pdf_paragraph
from core.provisioning_context import provisioning_channel
from core.rbac import Permission, has_permission
from fastapi import HTTPException
from security import create_access_token, hash_password
from models.user import User
from services.user_provisioning import create_staff_user, register_public_user


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_security_headers_present(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "strict-origin" in (r.headers.get("Referrer-Policy") or "")
    assert "frame-ancestors" in (r.headers.get("Content-Security-Policy") or "")


def test_clinical_schema_rejects_unknown_fields():
    from schemas.clinical import PatientIntakeCreate
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PatientIntakeCreate(
            first_name="A",
            last_name="B",
            age=20,
            unexpected_field="hack",
        )


def test_sql_probe_rejected():
    import pytest

    with pytest.raises(HTTPException) as exc:
        reject_suspicious_sql_input("1' OR 1=1 --", field="q")
    assert exc.value.status_code == 400


def test_output_encoding_escapes_markup():
    assert "&lt;script&gt;" in escape_html("<script>")
    assert "&lt;" in escape_pdf_paragraph("<b>x</b>")


def test_authorize_blocks_cross_clinic(db_session):
    with provisioning_channel("test_fixture"):
        user = User(
            email="authz.wave1@clinic.test",
            hashed_password=hash_password("StaffPass12!"),
            role="clinic_admin",
            clinic_id=1,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    try:
        authorize(user, roles=("clinic_admin",), clinic_id=2, db=db_session)
        assert False, "expected deny"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_assign_doctor_cross_clinic_denied(client, db_session):
    clinic_a = models.Clinic(name="Wave1 A", city="Conakry", is_active=True)
    clinic_b = models.Clinic(name="Wave1 B", city="Kindia", is_active=True)
    db_session.add_all([clinic_a, clinic_b])
    db_session.commit()
    db_session.refresh(clinic_a)
    db_session.refresh(clinic_b)

    with provisioning_channel("test_fixture"):
        admin = create_staff_user(
            db_session,
            email="admin.wave1a@clinic.test",
            password="StaffPass12!",
            role="clinic_admin",
            clinic_id=clinic_a.id,
        ).user
        doc = create_staff_user(
            db_session,
            email="doc.wave1@clinic.test",
            password="StaffPass12!",
            role="doctor",
            clinic_id=clinic_a.id,
        )
        doctor = db_session.query(models.Doctor).filter(models.Doctor.user_id == doc.user.id).first()
        assert doctor is not None

    r = client.patch(
        f"/clinical/doctors/{doctor.id}/clinic/{clinic_b.id}",
        headers=_headers(admin),
    )
    assert r.status_code == 403, r.text


def test_patient_delete_cross_clinic_denied(client, db_session):
    clinic_a = models.Clinic(name="Wave1 Pat A", city="Conakry", is_active=True)
    clinic_b = models.Clinic(name="Wave1 Pat B", city="Kindia", is_active=True)
    db_session.add_all([clinic_a, clinic_b])
    db_session.commit()
    db_session.refresh(clinic_a)
    db_session.refresh(clinic_b)

    patient = models.Patient(
        first_name="X",
        last_name="Y",
        age=30,
        gender="other",
        clinic_id=clinic_b.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    with provisioning_channel("test_fixture"):
        admin = create_staff_user(
            db_session,
            email="admin.wave1pat@clinic.test",
            password="StaffPass12!",
            role="clinic_admin",
            clinic_id=clinic_a.id,
        ).user

    r = client.delete(f"/patients/{patient.id}", headers=_headers(admin))
    assert r.status_code == 403, r.text


def test_search_sql_probe_blocked(client, db_session):
    clinic = models.Clinic(name="Wave1 Search", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)

    with provisioning_channel("test_fixture"):
        reception = create_staff_user(
            db_session,
            email="recv.wave1@clinic.test",
            password="StaffPass12!",
            role="receptionist",
            clinic_id=clinic.id,
        ).user

    r = client.get(
        "/clinical/reception/patients",
        params={"q": "union select password from users"},
        headers=_headers(reception),
    )
    assert r.status_code == 400, r.text


def test_audit_requires_admin_audit_permission(client, db_session):
    clinic = models.Clinic(name="Wave1 Audit", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)

    with provisioning_channel("test_fixture"):
        reception = create_staff_user(
            db_session,
            email="recv.audit.wave1@clinic.test",
            password="StaffPass12!",
            role="receptionist",
            clinic_id=clinic.id,
        ).user
    assert not has_permission(reception, Permission.ADMIN_AUDIT)

    r = client.get("/clinical/audit-logs", headers=_headers(reception))
    assert r.status_code == 403, r.text
    detail = str(r.json().get("detail", "")).lower()
    assert "permission denied" in detail
    assert "requires one of" not in detail
