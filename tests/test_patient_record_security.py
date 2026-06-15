"""
Security tests for A1 — server-side patient dossier (RBAC + audit log).
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta

import pytest

from models.clinical_audit_log import ClinicalAuditLog
from models.doctor import Doctor
from models.patient import Patient
from models.rendezvous import RendezVous
from security import create_access_token
from tests.clinic_fixtures import bind_clinic_booking
from services.user_provisioning import create_admin_user, register_public_user


def _auth_headers(user) -> dict[str, str]:
    token = create_access_token({"sub": user.email, "user_id": user.id, "user_role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def dossier_context(db_session):
    suffix = uuid.uuid4().hex[:8]

    patient_user = register_public_user(
        db_session, email=f"pat.dossier.{suffix}@test.gn", password="Secret12", role="patient"
    ).user
    doctor_a_user = register_public_user(
        db_session, email=f"dr.a.dossier.{suffix}@test.gn", password="Secret12", role="doctor"
    ).user
    doctor_b_user = register_public_user(
        db_session, email=f"dr.b.dossier.{suffix}@test.gn", password="Secret12", role="doctor"
    ).user
    admin = create_admin_user(
        db_session,
        email=f"admin.dossier.{suffix}@test.gn",
        password="AdminPass1",
        channel="test_fixture",
    ).user

    patient = db_session.query(Patient).filter(Patient.user_id == patient_user.id).first()
    doctor_a = db_session.query(Doctor).filter(Doctor.user_id == doctor_a_user.id).first()
    doctor_b = db_session.query(Doctor).filter(Doctor.user_id == doctor_b_user.id).first()
    clinic = bind_clinic_booking(db_session, doctor=doctor_a, patient=patient)

    rdv = RendezVous(
        patient_id=patient.id,
        doctor_id=doctor_a.id,
        clinic_id=clinic.id,
        date=datetime.utcnow() + timedelta(days=2),
        status="confirmed",
        payment_status="paid",
        consultation_type="teleconsultation",
    )
    db_session.add(rdv)
    db_session.commit()
    db_session.refresh(rdv)

    return {
        "patient": patient,
        "patient_user": patient_user,
        "doctor_a": doctor_a,
        "doctor_b": doctor_b,
        "doctor_a_user": doctor_a_user,
        "doctor_b_user": doctor_b_user,
        "admin_user": admin,
        "rdv": rdv,
        "patient_headers": _auth_headers(patient_user),
        "doctor_a_headers": _auth_headers(doctor_a_user),
        "doctor_b_headers": _auth_headers(doctor_b_user),
        "admin_headers": _auth_headers(admin),
    }


class TestPatientDossierRBAC:
    def test_patient_can_read_own_dossier(self, client, dossier_context):
        ctx = dossier_context
        response = client.get(f"/patients/{ctx['patient'].id}", headers=ctx["patient_headers"])
        assert response.status_code == 200
        assert response.json()["id"] == ctx["patient"].id

    def test_patient_cannot_read_other_dossier(self, client, dossier_context, db_session):
        ctx = dossier_context
        other = register_public_user(
            db_session, email=f"other.pat.{uuid.uuid4().hex[:6]}@test.gn", password="Secret12", role="patient"
        ).user
        other_patient = db_session.query(Patient).filter(Patient.user_id == other.id).first()
        response = client.get(f"/patients/{other_patient.id}", headers=ctx["patient_headers"])
        assert response.status_code == 403

    def test_linked_doctor_can_read_dossier(self, client, dossier_context):
        ctx = dossier_context
        response = client.get(f"/patients/{ctx['patient'].id}", headers=ctx["doctor_a_headers"])
        assert response.status_code == 200

    def test_unlinked_doctor_denied(self, client, dossier_context):
        ctx = dossier_context
        response = client.get(f"/patients/{ctx['patient'].id}", headers=ctx["doctor_b_headers"])
        assert response.status_code == 403

    def test_admin_can_read_any_dossier(self, client, dossier_context):
        ctx = dossier_context
        response = client.get(f"/patients/{ctx['patient'].id}", headers=ctx["admin_headers"])
        assert response.status_code == 200

    def test_patient_cannot_create_clinical_note(self, client, dossier_context):
        ctx = dossier_context
        response = client.post(
            f"/patients/{ctx['patient'].id}/notes",
            headers=ctx["patient_headers"],
            json={"note_type": "consultation", "contenu": "Tentative patient"},
        )
        assert response.status_code == 403

    def test_linked_doctor_can_create_note(self, client, dossier_context):
        ctx = dossier_context
        response = client.post(
            f"/patients/{ctx['patient'].id}/notes",
            headers=ctx["doctor_a_headers"],
            json={
                "note_type": "consultation",
                "contenu": "Suivi post-consultation",
                "appointment_id": ctx["rdv"].id,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["contenu"] == "Suivi post-consultation"
        assert body["doctor_id"] == ctx["doctor_a"].id

    def test_unlinked_doctor_cannot_create_note(self, client, dossier_context):
        ctx = dossier_context
        response = client.post(
            f"/patients/{ctx['patient'].id}/notes",
            headers=ctx["doctor_b_headers"],
            json={"note_type": "consultation", "contenu": "IDOR attempt"},
        )
        assert response.status_code == 403

    def test_linked_doctor_can_create_summary(self, client, dossier_context):
        ctx = dossier_context
        response = client.post(
            f"/patients/{ctx['patient'].id}/summaries",
            headers=ctx["doctor_a_headers"],
            json={
                "appointment_id": ctx["rdv"].id,
                "diagnostic": "Rhume viral",
                "traitement": "Repos",
                "recommandations": "Hydratation",
            },
        )
        assert response.status_code == 201
        assert response.json()["diagnostic"] == "Rhume viral"

    def test_patient_can_list_own_notes(self, client, dossier_context):
        ctx = dossier_context
        client.post(
            f"/patients/{ctx['patient'].id}/notes",
            headers=ctx["doctor_a_headers"],
            json={"note_type": "suivi", "contenu": "Note visible patient"},
        )
        response = client.get(f"/patients/{ctx['patient'].id}/notes", headers=ctx["patient_headers"])
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_unlinked_doctor_denied_timeline(self, client, dossier_context):
        ctx = dossier_context
        response = client.get(
            f"/patients/{ctx['patient'].id}/timeline", headers=ctx["doctor_b_headers"]
        )
        assert response.status_code == 403


class TestClinicalAuditLog:
    def test_read_patient_creates_audit_entry(self, client, dossier_context, db_session):
        ctx = dossier_context
        before = db_session.query(ClinicalAuditLog).count()
        client.get(f"/patients/{ctx['patient'].id}", headers=ctx["doctor_a_headers"])
        after = db_session.query(ClinicalAuditLog).count()
        assert after == before + 1
        log = (
            db_session.query(ClinicalAuditLog)
            .filter(ClinicalAuditLog.patient_id == ctx["patient"].id)
            .order_by(ClinicalAuditLog.id.desc())
            .first()
        )
        assert log.action == "read"
        assert log.resource_type == "patient"
        assert log.actor_role == "doctor"

    def test_create_note_creates_audit_entry(self, client, dossier_context, db_session):
        ctx = dossier_context
        response = client.post(
            f"/patients/{ctx['patient'].id}/notes",
            headers=ctx["doctor_a_headers"],
            json={"note_type": "urgence", "contenu": "Audit test note"},
        )
        assert response.status_code == 201
        note_id = response.json()["id"]
        log = (
            db_session.query(ClinicalAuditLog)
            .filter(
                ClinicalAuditLog.resource_type == "clinical_note",
                ClinicalAuditLog.resource_id == note_id,
            )
            .first()
        )
        assert log is not None
        assert log.action == "create"

    def test_list_summaries_creates_read_audit(self, client, dossier_context, db_session):
        ctx = dossier_context
        client.post(
            f"/patients/{ctx['patient'].id}/summaries",
            headers=ctx["admin_headers"],
            json={"diagnostic": "Test audit summaries list"},
        )
        client.get(f"/patients/{ctx['patient'].id}/summaries", headers=ctx["patient_headers"])
        log = (
            db_session.query(ClinicalAuditLog)
            .filter(
                ClinicalAuditLog.patient_id == ctx["patient"].id,
                ClinicalAuditLog.resource_type == "consultation_summaries",
            )
            .order_by(ClinicalAuditLog.id.desc())
            .first()
        )
        assert log is not None
        assert log.action == "read"
        assert log.actor_role == "patient"


class TestPatientDocuments:
    def test_doctor_can_upload_document(self, client, dossier_context):
        ctx = dossier_context
        pdf_bytes = b"%PDF-1.4\n% clinical test document\n"
        response = client.post(
            f"/patients/{ctx['patient'].id}/documents",
            headers=ctx["doctor_a_headers"],
            files={"file": ("ordonnance.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"type_document": "ordonnance"},
        )
        assert response.status_code == 201
        assert response.json()["type_document"] == "ordonnance"

    def test_patient_can_download_document(self, client, dossier_context):
        ctx = dossier_context
        pdf_bytes = b"%PDF-1.4\n% patient download test\n"
        upload = client.post(
            f"/patients/{ctx['patient'].id}/documents",
            headers=ctx["doctor_a_headers"],
            files={"file": ("analyse.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"type_document": "analyse"},
        )
        doc_id = upload.json()["id"]
        response = client.get(
            f"/patients/{ctx['patient'].id}/documents/{doc_id}/download",
            headers=ctx["patient_headers"],
        )
        assert response.status_code == 200
        assert b"%PDF" in response.content
