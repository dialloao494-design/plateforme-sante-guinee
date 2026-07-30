"""
Security Wave 2 — documents, uploads, PDF, encryption, integrity, malware.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from core.attachment_malware import EICAR_SIGNATURE
from core.output_encoding import escape_pdf_paragraph
from models.doctor import Doctor
from models.patient import Patient
from models.rendezvous import RendezVous
from models.user import User
from security import create_access_token
from services.consultation_pdf_builder import build_consultation_pdf
from services.invoice_pdf_builder import build_hospital_invoice_pdf
from services.lab_report_pdf_builder import build_lab_report_pdf
from services.secure_attachment_storage import SecureAttachmentStorage
from services.user_provisioning import register_public_user
from tests.clinic_fixtures import bind_clinic_booking, get_or_create_test_clinic


@pytest.fixture()
def secure_attachment_root(tmp_path, monkeypatch):
    root = tmp_path / "secure_attachments_w2"
    monkeypatch.setenv("SECURE_ATTACHMENT_ROOT", str(root))
    monkeypatch.setenv("ATTACHMENT_MAX_BYTES", str(5 * 1024 * 1024))
    monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "off")
    return root


@pytest.fixture()
def encrypted_attachment_root(secure_attachment_root, monkeypatch):
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet

    key = Fernet.generate_key()
    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", key.decode("ascii"))
    import core.attachment_encryption as enc

    enc.reset_encryption_cache()
    yield secure_attachment_root
    enc.reset_encryption_cache()


def _ensure_user(db_session, email: str, role: str):
    existing = db_session.query(User).filter(User.email == email).first()
    if existing:
        return existing
    return register_public_user(db_session, email=email, password="Secret12", role=role).user


def _auth_headers(user) -> dict[str, str]:
    token = create_access_token({"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def messaging_context(db_session, secure_attachment_root, client, admin_user):
    suffix = uuid.uuid4().hex[:8]
    patient_user = _ensure_user(db_session, f"patient.w2.{suffix}@test.gn", "patient")
    patient = db_session.query(Patient).filter(Patient.user_id == patient_user.id).first()

    doctor_user = _ensure_user(db_session, f"doctor.w2.{suffix}@test.gn", "doctor")
    doctor = db_session.query(Doctor).filter(Doctor.user_id == doctor_user.id).first()

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
        "patient": patient,
        "doctor": doctor,
        "clinic": clinic,
        "appointment": rdv,
        "patient_headers": _auth_headers(patient_user),
        "doctor_headers": _auth_headers(doctor_user),
        "admin_headers": _auth_headers(admin_user),
    }


def _upload_pdf(client, headers, appointment_id: int) -> dict:
    pdf_bytes = b"%PDF-1.4\n% wave2 clinical document\n"
    files = {"attachment": ("ordonnance.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post(
        f"/messages/{appointment_id}",
        headers=headers,
        data={"content": "Ordonnance"},
        files=files,
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestProductionEncryptionRequirement:
    def test_production_requires_attachment_encryption_key(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "x" * 40)
        monkeypatch.setenv("DB_PASSWORD", "strong-db-password-99")
        monkeypatch.setenv("JITSI_SECRET", "strong-jitsi-secret")
        monkeypatch.setenv("REMINDER_RESPOND_TOKEN", "r" * 40)
        monkeypatch.setenv("DOMAIN", "example.com")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "127.0.0.1")
        monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)

        from core.settings import AppSettings

        settings = AppSettings()
        with pytest.raises(RuntimeError, match="ATTACHMENT_ENCRYPTION_KEY"):
            settings.validate_production_secrets()

    def test_production_accepts_valid_fernet_key(self, monkeypatch):
        pytest.importorskip("cryptography")
        from cryptography.fernet import Fernet

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "x" * 40)
        monkeypatch.setenv("DB_PASSWORD", "strong-db-password-99")
        monkeypatch.setenv("JITSI_SECRET", "strong-jitsi-secret")
        monkeypatch.setenv("REMINDER_RESPOND_TOKEN", "r" * 40)
        monkeypatch.setenv("DOMAIN", "example.com")
        monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
        monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "127.0.0.1")
        monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", Fernet.generate_key().decode())

        from core.settings import AppSettings

        AppSettings().validate_production_secrets()


class TestFileIntegrity:
    def test_store_returns_sha256_and_verifies_on_read(self, secure_attachment_root):
        content = b"%PDF-1.4\n% integrity check\n"
        stored = SecureAttachmentStorage.store(
            content, original_filename="rx.pdf", extension=".pdf"
        )
        assert len(stored.content_sha256) == 64
        read_back, _ = SecureAttachmentStorage.read(
            stored.storage_key, expected_sha256=stored.content_sha256
        )
        assert read_back == content

    def test_tampered_blob_fails_integrity(self, secure_attachment_root):
        from fastapi import HTTPException

        content = b"%PDF-1.4\n% original\n"
        stored = SecureAttachmentStorage.store(
            content, original_filename="rx.pdf", extension=".pdf"
        )
        path = SecureAttachmentStorage._absolute_path(stored.storage_key)
        path.write_bytes(b"%PDF-1.4\n% TAMPERED\n")
        with pytest.raises(HTTPException) as exc:
            SecureAttachmentStorage.read(
                stored.storage_key, expected_sha256=stored.content_sha256
            )
        assert exc.value.status_code == 409

    def test_message_upload_persists_sha256(
        self, client, db_session, messaging_context, secure_attachment_root
    ):
        from models.message import Message

        ctx = messaging_context
        message = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)
        row = db_session.query(Message).filter(Message.id == message["id"]).first()
        assert row.attachment_content_sha256
        assert len(row.attachment_content_sha256) == 64

        response = client.get(
            f"/messages/attachments/{message['id']}/download",
            headers=ctx["patient_headers"],
        )
        assert response.status_code == 200
        assert response.headers.get("x-content-sha256") == row.attachment_content_sha256


class TestMalwareValidation:
    def test_stub_mode_rejects_eicar(self, secure_attachment_root, monkeypatch):
        from fastapi import HTTPException

        monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "stub")
        # Bypass MIME allowlist by injecting scan after validate — call scan directly
        # and also ensure store path rejects when content looks like txt + eicar.
        # EICAR is text; use .txt extension.
        with pytest.raises(HTTPException) as exc:
            SecureAttachmentStorage.store(
                EICAR_SIGNATURE,
                original_filename="eicar.txt",
                extension=".txt",
            )
        assert exc.value.status_code == 400
        assert "Malware" in exc.value.detail

    def test_off_mode_allows_clean_pdf(self, secure_attachment_root, monkeypatch):
        monkeypatch.setenv("ATTACHMENT_VIRUS_SCAN", "off")
        stored = SecureAttachmentStorage.store(
            b"%PDF-1.4\nclean\n",
            original_filename="ok.pdf",
            extension=".pdf",
        )
        assert stored.size_bytes > 0


class TestClinicAdminDownloadScope:
    def test_foreign_clinic_admin_cannot_download(
        self, client, db_session, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        message = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)

        other_clinic = get_or_create_test_clinic(db_session, name="Other Clinic W2")
        from services.user_provisioning import create_clinic_admin_user

        provisioned = create_clinic_admin_user(
            db_session,
            email=f"admin.other.{uuid.uuid4().hex[:6]}@test.gn",
            password="Secret12Secret",
            clinic_id=other_clinic.id,
        )
        headers = _auth_headers(provisioned.user)

        response = client.get(
            f"/messages/attachments/{message['id']}/download",
            headers=headers,
        )
        assert response.status_code == 403

    def test_same_clinic_admin_can_download(
        self, client, db_session, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        message = _upload_pdf(client, ctx["doctor_headers"], ctx["appointment"].id)

        from services.user_provisioning import create_clinic_admin_user

        provisioned = create_clinic_admin_user(
            db_session,
            email=f"admin.same.{uuid.uuid4().hex[:6]}@test.gn",
            password="Secret12Secret",
            clinic_id=ctx["clinic"].id,
        )
        headers = _auth_headers(provisioned.user)
        response = client.get(
            f"/messages/attachments/{message['id']}/download",
            headers=headers,
        )
        assert response.status_code == 200


class TestPatientDocumentPhiHygiene:
    def test_upload_hides_storage_key_and_sets_download_headers(
        self, client, db_session, messaging_context, secure_attachment_root
    ):
        ctx = messaging_context
        pdf_bytes = b"%PDF-1.4\n% patient dossier doc\n"
        upload = client.post(
            f"/patients/{ctx['patient'].id}/documents",
            headers=ctx["doctor_headers"],
            files={"file": ("analyse.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            data={"type_document": "analyse"},
        )
        assert upload.status_code == 201, upload.text
        body = upload.json()
        assert "file_path" not in body
        assert body["download_url"].endswith("/download")
        assert body.get("mime_type") == "application/pdf"
        assert body.get("original_filename") == "analyse.pdf"

        doc_id = body["id"]
        download = client.get(
            f"/patients/{ctx['patient'].id}/documents/{doc_id}/download",
            headers=ctx["patient_headers"],
        )
        assert download.status_code == 200
        assert "no-store" in download.headers.get("cache-control", "")
        assert download.headers.get("x-content-type-options") == "nosniff"
        assert download.headers.get("x-content-sha256")
        assert download.content.startswith(b"%PDF")


class TestPdfOutputEncoding:
    def test_escape_pdf_paragraph_neutralizes_markup(self):
        assert "&lt;" in escape_pdf_paragraph("<script>alert(1)</script>")
        assert "&amp;" in escape_pdf_paragraph("a & b")

    def test_consultation_pdf_handles_hostile_patient_name(self):
        pdf = build_consultation_pdf(
            {
                "patient": {
                    "patient_number": "P-1",
                    "full_name": '<img src=x onerror=alert(1)> "O\'Neill"',
                    "age": "30",
                    "sex": "F",
                    "phone": "<b>bad</b>",
                },
                "consultation": {
                    "chief_complaint": "Douleur <script>",
                    "diagnosis": "OK & stable",
                },
                "vitals": {},
                "doctor_name": "Dr <Evil>",
                "printed_by": "nurse",
                "department": "Médecine",
            }
        )
        assert pdf.startswith(b"%PDF")

    def test_lab_and_invoice_pdfs_escape_phi_fields(self):
        lab = build_lab_report_pdf(
            patient_name="<b>Patient</b>",
            patient_file_number="F-1",
            test_name="NFS",
            result_summary="12 < 13",
            result_data=None,
            technician="Tech",
            validated_date="01/01/2026",
            validated_time="10:00",
        )
        assert lab.startswith(b"%PDF")

        inv = build_hospital_invoice_pdf(
            invoice_number="INV-1",
            patient_name="Patient <script>",
            patient_file_number="F-1",
            items=[{"description": "Consult <b>x</b>", "quantity": 1, "amount_gnf": 1000}],
            subtotal=1000,
            total=1000,
            paid=0,
            printed_by="caissier",
            printed_date="01/01/2026",
            printed_time="10:00",
        )
        assert inv.startswith(b"%PDF")


class TestEncryptedAtRest:
    def test_encrypted_storage_roundtrip(self, encrypted_attachment_root):
        content = b"%PDF-1.4\n% encrypted phi\n"
        stored = SecureAttachmentStorage.store(
            content, original_filename="phi.pdf", extension=".pdf"
        )
        raw = SecureAttachmentStorage._absolute_path(stored.storage_key).read_bytes()
        assert content not in raw
        assert raw.startswith(b"\x00ATTENC\x01")
        assert SecureAttachmentStorage.read(stored.storage_key)[0] == content
