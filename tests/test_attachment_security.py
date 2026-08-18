"""
Security tests for clinical message attachments (audit item #3).

Verifies that attachments are never served without authentication and that
appointment-scoped RBAC is enforced on download.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from main import app
from models.attachment_access_log import AttachmentAccessLog
from models.clinical_audit_log import ClinicalAuditLog
from models.doctor import Doctor
from models.message import Message
from models.patient import Patient
from models.rendezvous import RendezVous
from security import create_access_token
from services.secure_attachment_storage import SecureAttachmentStorage
from tests.clinic_fixtures import bind_clinic_booking
from services.user_provisioning import register_public_user


@pytest.fixture()
def secure_attachment_root(tmp_path, monkeypatch):
    root = tmp_path / "secure_attachments"
    monkeypatch.setenv("SECURE_ATTACHMENT_ROOT", str(root))
    monkeypatch.setenv("ATTACHMENT_MAX_BYTES", str(5 * 1024 * 1024))
    return root


@pytest.fixture()
def encrypted_attachment_root(secure_attachment_root, monkeypatch):
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", key.decode("ascii"))
    # Reset cached Fernet instance between tests.
    import core.attachment_encryption as enc

    enc._fernet = None
    enc._initialized = False
    return secure_attachment_root


def _ensure_user(db_session, email: str, role: str):
    from models.user import User

    existing = db_session.query(User).filter(User.email == email).first()
    if existing:
        return existing
    return register_public_user(db_session, email=email, password="Secret12Pass!", role=role).user


def _auth_headers(user) -> dict[str, str]:
    token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def messaging_context(db_session, secure_attachment_root, client, admin_user):
    suffix = uuid.uuid4().hex[:8]
    patient_user = _ensure_user(db_session, f"patient.msg.{suffix}@test.gn", "patient")
    patient = db_session.query(Patient).filter(Patient.user_id == patient_user.id).first()

    doctor_user = _ensure_user(db_session, f"doctor.msg.{suffix}@test.gn", "doctor")
    doctor = db_session.query(Doctor).filter(Doctor.user_id == doctor_user.id).first()

    other_patient_user = _ensure_user(db_session, f"other.msg.{suffix}@test.gn", "patient")
    db_session.query(Patient).filter(Patient.user_id == other_patient_user.id).first()

    admin_user = admin_user

    clinic = bind_clinic_booking(db_session, doctor=doctor, patient=patient)

    rdv = RendezVous(
        date=datetime.utcnow() + timedelta(days=1),
        duration_minutes=30,
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=clinic.id,
        status="confirmed",
        payment_status="paid",
        price=45000.0,
        consultation_type="physical",
    )
    db_session.add(rdv)
    db_session.commit()
    db_session.refresh(rdv)

    return {
        "patient_user": patient_user,
        "doctor_user": doctor_user,
        "other_patient_user": other_patient_user,
        "admin_user": admin_user,
        "patient": patient,
        "doctor": doctor,
        "appointment": rdv,
        "patient_headers": _auth_headers(patient_user),
        "doctor_headers": _auth_headers(doctor_user),
        "other_patient_headers": _auth_headers(other_patient_user),
        "admin_headers": _auth_headers(admin_user),
    }


def _upload_pdf(client, headers, appointment_id: int, filename: str = "ordonnance.pdf") -> dict:
    pdf_bytes = b"%PDF-1.4\n% clinical test document\n"
    files = {"attachment": (filename, io.BytesIO(pdf_bytes), "application/pdf")}
    data = {"content": "Ordonnance jointe"}
    response = client.post(f"/messages/{appointment_id}", headers=headers, data=data, files=files)
    assert response.status_code == 200, response.text
    return response.json()


class TestPublicUploadPathBlocked:
    def test_legacy_uploads_url_returns_404(self, client, secure_attachment_root):
        legacy_file = Path("uploads/messages/appointment_999/secret.pdf")
        legacy_file.parent.mkdir(parents=True, exist_ok=True)
        legacy_file.write_bytes(b"%PDF-1.4\nsecret")

        response = client.get("/uploads/messages/appointment_999/secret.pdf")
        assert response.status_code == 404

    def test_legacy_uploads_head_returns_404(self, client):
        response = client.head("/uploads/messages/appointment_1/file.pdf")
        assert response.status_code == 404

    def test_uploads_path_outside_messages_subtree_still_blocked(self, client, tmp_path):
        secret = tmp_path / "etc_passwd_leak.pdf"
        secret.write_bytes(b"%PDF-1.4\nsecret")
        # Even if someone symlinked or placed a file, HTTP must not serve it.
        response = client.get("/uploads/secure/../../etc/passwd")
        assert response.status_code == 404


class TestAttachmentDownloadAuth:
    def test_download_without_token_rejected(self, client, messaging_context, secure_attachment_root):
        ctx = messaging_context
        message = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)

        response = client.get(f"/messages/attachments/{message['id']}/download")
        assert response.status_code == 401

    def test_cross_patient_download_forbidden_is_audited(
        self, client, db_session, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        message = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)

        response = client.get(
            f"/messages/attachments/{message['id']}/download",
            headers=ctx["other_patient_headers"],
        )
        assert response.status_code == 403
        denied = (
            db_session.query(ClinicalAuditLog)
            .filter(
                ClinicalAuditLog.action == "denied_download",
                ClinicalAuditLog.resource_type == "message_attachment",
                ClinicalAuditLog.resource_id == message["id"],
            )
            .one()
        )
        assert denied.actor_id == ctx["other_patient_user"].id
        assert denied.clinic_id == ctx["appointment"].clinic_id

    def test_patient_can_download_own_appointment_attachment(
        self, client, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        message = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)

        response = client.get(
            f"/messages/attachments/{message['id']}/download",
            headers=ctx["patient_headers"],
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")
        assert "no-store" in response.headers.get("cache-control", "")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_doctor_can_download_appointment_attachment(
        self, client, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        png_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"attachment": ("resultat.png", io.BytesIO(png_bytes), "image/png")}
        data = {"content": "Imagerie"}
        upload = client.post(
            f"/messages/{ctx['appointment'].id}",
            headers=ctx["patient_headers"],
            data=data,
            files=files,
        )
        assert upload.status_code == 200
        message = upload.json()

        response = client.get(
            f"/messages/attachments/{message['id']}/download",
            headers=ctx["doctor_headers"],
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("image/png")

    def test_admin_can_download_with_audit_trail(
        self, client, db_session, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        message = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)

        response = client.get(
            f"/messages/attachments/{message['id']}/download",
            headers=ctx["admin_headers"],
        )
        assert response.status_code == 200

        logs = (
            db_session.query(AttachmentAccessLog)
            .filter(AttachmentAccessLog.message_id == message["id"])
            .all()
        )
        assert len(logs) == 1
        assert logs[0].user_role == "platform_owner"
        assert logs[0].storage_kind == "secure"


class TestMessageListDoesNotExposePublicUrls:
    def test_list_messages_returns_authenticated_download_path_only(
        self, client, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        uploaded = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)

        response = client.get(f"/messages/{ctx['appointment'].id}", headers=ctx["doctor_headers"])
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        row = payload[0]
        assert row["has_attachment"] is True
        assert row["attachment_download_url"] == f"/messages/attachments/{uploaded['id']}/download"
        assert "attachment_url" not in row
        assert not str(row.get("attachment_download_url", "")).startswith("/uploads/")


class TestLegacyAttachmentMigrationPath:
    def test_legacy_attachment_url_readable_via_authenticated_download(
        self, client, db_session, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        legacy_dir = Path("uploads/messages") / f"appointment_{ctx['appointment'].id}"
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_name = "legacy_ordonnance.pdf"
        legacy_path = legacy_dir / legacy_name
        legacy_path.write_bytes(b"%PDF-1.4\nlegacy clinical document")

        message = Message(
            appointment_id=ctx["appointment"].id,
            sender_user_id=ctx["doctor_user"].id,
            content="Legacy message",
            attachment_name=legacy_name,
            attachment_url=f"/uploads/messages/appointment_{ctx['appointment'].id}/{legacy_name}",
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)

        response = client.get(
            f"/messages/attachments/{message.id}/download",
            headers=ctx["patient_headers"],
        )
        assert response.status_code == 200
        assert b"legacy clinical" in response.content

        public = client.get(message.attachment_url)
        assert public.status_code == 404

    def test_legacy_path_traversal_rejected(self, db_session, messaging_context):
        ctx = messaging_context
        traversal_url = "/uploads/messages/../../secret.pdf"
        assert SecureAttachmentStorage.resolve_legacy_public_url(traversal_url) is None

        message = Message(
            appointment_id=ctx["appointment"].id,
            sender_user_id=ctx["doctor_user"].id,
            content="Traversal attempt",
            attachment_name="secret.pdf",
            attachment_url=traversal_url,
        )
        db_session.add(message)
        db_session.commit()
        db_session.refresh(message)

        # Service layer must not resolve traversal paths.
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            SecureAttachmentStorage.read_legacy(traversal_url)
        assert exc.value.status_code == 404


class TestSecureStorageHardening:
    def test_storage_key_path_traversal_rejected(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            SecureAttachmentStorage.read("../etc/passwd")
        assert exc.value.status_code == 400

    def test_encrypted_at_rest_when_key_configured(self, encrypted_attachment_root):
        content = b"%PDF-1.4\nencrypted clinical document"
        stored = SecureAttachmentStorage.store(
            content,
            original_filename="ordonnance.pdf",
            extension=".pdf",
        )
        raw_on_disk = SecureAttachmentStorage._absolute_path(stored.storage_key).read_bytes()
        assert content not in raw_on_disk
        read_back, _ = SecureAttachmentStorage.read(stored.storage_key)
        assert read_back == content


class TestAttachmentUploadValidation:
    def test_disallowed_extension_rejected(self, client, messaging_context, secure_attachment_root):
        ctx = messaging_context
        files = {"attachment": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
        response = client.post(
            f"/messages/{ctx['appointment'].id}",
            headers=ctx["doctor_headers"],
            data={"content": "test"},
            files=files,
        )
        assert response.status_code == 400

    def test_mismatched_extension_and_content_rejected(
        self, client, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        files = {"attachment": ("fake.pdf", io.BytesIO(b"not a pdf"), "application/pdf")}
        response = client.post(
            f"/messages/{ctx['appointment'].id}",
            headers=ctx["doctor_headers"],
            data={"content": "test"},
            files=files,
        )
        assert response.status_code == 400

    def test_oversized_attachment_rejected(self, client, messaging_context, monkeypatch):
        ctx = messaging_context
        monkeypatch.setattr("services.secure_attachment_storage.MAX_ATTACHMENT_BYTES", 128)
        pdf_bytes = b"%PDF-1.4\n" + b"x" * 200
        files = {"attachment": ("big.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        response = client.post(
            f"/messages/{ctx['appointment'].id}",
            headers=ctx["doctor_headers"],
            data={"content": "test"},
            files=files,
        )
        assert response.status_code == 413
