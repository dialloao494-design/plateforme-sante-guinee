"""Regression suite — release-blocking tenant / webhook mutation gaps."""

from __future__ import annotations

from datetime import datetime, timedelta

import models
import pytest
from core.patient_ownership_policy import PatientOwnershipPolicy
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password
from services.message_attachment_service import assert_appointment_access


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
            "tv": int(getattr(user, "token_version", 0) or 0),
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _clinic(db, name: str) -> models.Clinic:
    c = models.Clinic(name=name, city="Conakry", is_active=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _user(db, *, email: str, role: str, clinic_id=None):
    with provisioning_channel("test_fixture"):
        u = models.User(
            email=email,
            hashed_password=hash_password("StrongPass12!"),
            role=role,
            clinic_id=clinic_id,
            is_active=True,
            token_version=0,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _doctor(db, *, clinic_id: int, email: str) -> models.Doctor:
    u = _user(db, email=email, role="doctor", clinic_id=clinic_id)
    d = models.Doctor(
        user_id=u.id,
        first_name="Doc",
        last_name="X",
        specialty="gp",
        city="Conakry",
        phone="620000000",
        clinic_id=clinic_id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _patient(db, *, clinic_id: int, user_id=None, name: str = "Pat") -> models.Patient:
    p = models.Patient(
        user_id=user_id,
        first_name=name,
        last_name="Test",
        age=30,
        gender="f",
        clinic_id=clinic_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_message_attachment_clinic_admin_cannot_cross_clinic(db_session):
    c1 = _clinic(db_session, "Att-C1")
    c2 = _clinic(db_session, "Att-C2")
    admin = _user(db_session, email="att.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    patient = _patient(db_session, clinic_id=c2.id)
    doctor = _doctor(db_session, clinic_id=c2.id, email="att.doc@test.gn")
    appt = models.RendezVous(
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=c2.id,
        date=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        status="pending",
    )
    db_session.add(appt)
    db_session.commit()

    with pytest.raises(Exception) as exc:
        assert_appointment_access(db_session, appt, admin)
    assert getattr(exc.value, "status_code", None) == 403


def test_whatsapp_webhook_rejects_missing_secret_and_bad_signature(client, monkeypatch):
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    body = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "text": {"body": "ANNULER"},
                                    "context": {"appointment_id": 99},
                                    "from": "224620000000",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    r = client.post("/clinical/reminders/whatsapp/webhook", json=body)
    assert r.status_code == 403

    monkeypatch.setenv("WHATSAPP_APP_SECRET", "secret-for-hardening")
    r2 = client.post(
        "/clinical/reminders/whatsapp/webhook",
        json=body,
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )
    assert r2.status_code == 403


def test_patient_update_and_delete_cross_clinic_denied(client, db_session):
    c1 = _clinic(db_session, "Pat-C1")
    c2 = _clinic(db_session, "Pat-C2")
    admin = _user(db_session, email="pat.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    foreign = _patient(db_session, clinic_id=c2.id, name="Foreign")

    r_put = client.put(
        f"/patients/{foreign.id}",
        json={
            "user_id": None,
            "first_name": "Hacked",
            "last_name": "Name",
            "age": 99,
            "gender": "x",
        },
        headers=_auth(admin),
    )
    assert r_put.status_code == 403, r_put.text

    r_del = client.delete(f"/patients/{foreign.id}", headers=_auth(admin))
    assert r_del.status_code == 403, r_del.text

    db_session.refresh(foreign)
    assert foreign.first_name == "Foreign"
    assert foreign.is_archived is False


def test_patient_create_rejects_foreign_user_link(client, db_session):
    c1 = _clinic(db_session, "Create-C1")
    c2 = _clinic(db_session, "Create-C2")
    admin = _user(db_session, email="create.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    foreign_user = _user(db_session, email="foreign.pat@test.gn", role="patient", clinic_id=c2.id)

    r = client.post(
        "/patients/",
        json={
            "user_id": foreign_user.id,
            "first_name": "Bad",
            "last_name": "Link",
            "age": 22,
            "gender": "f",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 403, r.text


def test_patient_create_requires_account_for_clinic_admin(client, db_session):
    c1 = _clinic(db_session, "Req-C1")
    admin = _user(db_session, email="req.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    r = client.post(
        "/patients/",
        json={"first_name": "No", "last_name": "User", "age": 20, "gender": "m"},
        headers=_auth(admin),
    )
    assert r.status_code == 400, r.text


def test_patient_create_assigns_actor_clinic(client, db_session):
    c1 = _clinic(db_session, "Own-C1")
    admin = _user(db_session, email="own.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    account = _user(db_session, email="own.pat@test.gn", role="patient", clinic_id=c1.id)

    r = client.post(
        "/patients/",
        json={
            "user_id": account.id,
            "first_name": "Aissatou",
            "last_name": "Bah",
            "age": 28,
            "gender": "f",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["clinic_id"] == c1.id
    assert body["user_id"] == account.id


def test_account_candidates_are_clinic_scoped(client, db_session):
    c1 = _clinic(db_session, "Cand-C1")
    c2 = _clinic(db_session, "Cand-C2")
    admin = _user(db_session, email="cand.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    local = _user(db_session, email="local.candidate@test.gn", role="patient", clinic_id=c1.id)
    _user(db_session, email="foreign.candidate@test.gn", role="patient", clinic_id=c2.id)

    r = client.get(
        "/patients/account-candidates",
        params={"q": "candidate"},
        headers=_auth(admin),
    )
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()}
    assert local.id in ids
    assert all(row["clinic_id"] == c1.id for row in r.json())


def test_doctor_reassignment_cross_clinic_denied(client, db_session):
    c1 = _clinic(db_session, "Doc-C1")
    c2 = _clinic(db_session, "Doc-C2")
    admin = _user(db_session, email="reassign.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    foreign_doctor = _doctor(db_session, clinic_id=c2.id, email="foreign.doc@test.gn")

    r = client.patch(
        f"/clinical/doctors/{foreign_doctor.id}/clinic/{c1.id}",
        headers=_auth(admin),
    )
    assert r.status_code == 403, r.text
    db_session.refresh(foreign_doctor)
    assert foreign_doctor.clinic_id == c2.id


def test_doctor_reassignment_cannot_exile_to_other_clinic(client, db_session):
    c1 = _clinic(db_session, "Exile-C1")
    c2 = _clinic(db_session, "Exile-C2")
    admin = _user(db_session, email="exile.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    local_doctor = _doctor(db_session, clinic_id=c1.id, email="local.doc@test.gn")

    r = client.patch(
        f"/clinical/doctors/{local_doctor.id}/clinic/{c2.id}",
        headers=_auth(admin),
    )
    assert r.status_code == 403, r.text
    db_session.refresh(local_doctor)
    assert local_doctor.clinic_id == c1.id


def test_rendezvous_status_patch_cross_clinic_denied(client, db_session):
    c1 = _clinic(db_session, "Rdv-C1")
    c2 = _clinic(db_session, "Rdv-C2")
    admin = _user(db_session, email="rdv.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    patient = _patient(db_session, clinic_id=c2.id)
    doctor = _doctor(db_session, clinic_id=c2.id, email="rdv.doc@test.gn")
    appt = models.RendezVous(
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=c2.id,
        date=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        status="pending",
    )
    db_session.add(appt)
    db_session.commit()

    r = client.patch(
        f"/rendezvous/{appt.id}",
        json={"status": "cancelled"},
        headers=_auth(admin),
    )
    assert r.status_code in (403, 404), r.text
    db_session.refresh(appt)
    assert appt.status == "pending"


def test_patient_ownership_policy_rejects_null_clinic_patient(db_session):
    c1 = _clinic(db_session, "Null-C1")
    admin = _user(db_session, email="null.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    orphan = models.Patient(
        first_name="Orphan",
        last_name="Rec",
        age=40,
        gender="m",
        clinic_id=None,
    )
    db_session.add(orphan)
    db_session.commit()

    with pytest.raises(Exception) as exc:
        PatientOwnershipPolicy.assert_can_mutate_patient(db_session, admin, orphan)
    assert getattr(exc.value, "status_code", None) == 403


def test_alembic_upgrade_fail_closed_in_production(monkeypatch):
    from database_migrations import run_alembic_upgrade_head

    monkeypatch.setenv("ENVIRONMENT", "production")

    def _boom(*_a, **_k):
        raise RuntimeError("simulated alembic failure")

    monkeypatch.setattr("alembic.command.upgrade", _boom)
    with pytest.raises(RuntimeError, match="refusing to start"):
        run_alembic_upgrade_head(fail_closed=True)
