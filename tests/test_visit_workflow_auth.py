"""Visit workflow queues and auth register+login."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import models
from models.visit_workflow import PatientVisitWorkflow, PatientVisitWorkflowStep
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password, verify_password


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
            "session_version": int(getattr(user, "session_version", 0) or 0),
            "tv": int(getattr(user, "token_version", 0) or 0),
        }
    )
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_token_and_login_works(client, db_session):
    email = f"reg.flow.{uuid.uuid4().hex[:10]}@example.com"
    password = "SecurePass12!"
    r = client.post("/auth/register", json={"email": email, "password": password, "role": "doctor"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["access_token"]
    assert body["role"] == "doctor"
    assert body.get("doctor_id")

    user = db_session.query(models.User).filter(models.User.email == email).first()
    assert user is not None
    assert verify_password(password, user.hashed_password)

    r2 = client.post("/auth/login-json", json={"email": email, "password": password})
    assert r2.status_code == 200


def test_child_visit_workflow_advances(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"WF Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"recv.wf.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        nutritionist = models.User(
            email=f"nutri.wf.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="nutritionist",
            clinic_id=clinic_id,
        )
        db_session.add_all([reception, nutritionist])
        db_session.commit()
        db_session.refresh(reception)
        db_session.refresh(nutritionist)

    r = client.post(
        "/clinical/reception/patients",
        json={
            "first_name": "Child",
            "last_name": "Workflow",
            "age": 5,
            "gender": "F",
            "phone": "+224622000999",
        },
        headers=_auth(reception),
    )
    patient_id = r.json()["id"]

    r = client.post(
        "/clinical/workflow/visits",
        json={"patient_id": patient_id, "workflow_type": "child"},
        headers=_auth(reception),
    )
    assert r.status_code == 201, r.text
    wf_id = r.json()["id"]
    assert r.json()["current_department"] == "reception"

    r = client.get("/clinical/workflow/queue/reception", headers=_auth(reception))
    assert any(row["id"] == wf_id for row in r.json())

    r = client.post(f"/clinical/workflow/visits/{wf_id}/complete/reception", headers=_auth(reception))
    assert r.status_code == 200
    assert r.json()["current_department"] == "nutrition"

    r = client.get("/clinical/workflow/queue/nutrition", headers=_auth(nutritionist))
    assert any(row["id"] == wf_id for row in r.json())

    r = client.post(f"/clinical/workflow/visits/{wf_id}/complete/nutrition", headers=_auth(nutritionist))
    assert r.json()["current_department"] == "pev"


def test_pev_agent_can_read_and_complete_pev_queue(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    clinic = models.Clinic(name=f"PEV Clinic {suffix}", city="Conakry")
    db_session.add(clinic)
    db_session.flush()
    with provisioning_channel("test_fixture"):
        pev_agent = models.User(
            email=f"pev.wf.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="pev_agent",
            clinic_id=clinic.id,
        )
        db_session.add(pev_agent)
        db_session.flush()
        db_session.add(models.ClinicStaff(clinic_id=clinic.id, user_id=pev_agent.id, is_active=True))
        patient = models.Patient(
            clinic_id=clinic.id,
            first_name="Child",
            last_name="PEV",
            age=2,
            gender="F",
        )
        db_session.add(patient)
        db_session.flush()
        workflow = PatientVisitWorkflow(
            clinic_id=clinic.id,
            patient_id=patient.id,
            workflow_type="child",
            current_department="pev",
            status="active",
        )
        db_session.add(workflow)
        db_session.flush()
        db_session.add(PatientVisitWorkflowStep(
            workflow_id=workflow.id,
            department="pev",
            step_order=3,
            status="in_progress",
        ))
        db_session.commit()

    queue = client.get("/clinical/workflow/queue/pev", headers=_auth(pev_agent))
    assert queue.status_code == 200, queue.text
    assert any(item["id"] == workflow.id for item in queue.json())

    completed = client.post(
        f"/clinical/workflow/visits/{workflow.id}/complete/pev",
        headers=_auth(pev_agent),
    )
    assert completed.status_code == 200, completed.text
