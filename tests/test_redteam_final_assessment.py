"""Red Team final assessment — Critical/High exploit regressions."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import models
import pytest
from core.reminder_security import verify_reminder_respond_token
from core.update_security import UpdateSecurityError, load_and_verify_package, write_signed_package
from core.whatsapp_webhook_security import WhatsAppWebhookAuthError, verify_whatsapp_signature
from models.user import User
from security import create_access_token, decode_access_token, hash_password
from services.auth_session_service import issue_refresh_token, rotate_refresh_token
from services.message_attachment_service import assert_appointment_access
from services.user_provisioning import (
    PlatformOwnerSetupClosedError,
    platform_owner_exists,
    setup_first_platform_owner,
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _make_clinic(db_session, name: str = "Clinic A") -> models.Clinic:
    clinic = models.Clinic(name=name, city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)
    return clinic


def _make_user(db_session, *, email: str, role: str, password: str = "StrongPass12!", clinic_id=None) -> User:
    from core.provisioning_context import provisioning_channel

    with provisioning_channel("test_fixture"):
        user = User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
            clinic_id=clinic_id,
            token_version=0,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def _make_doctor(db_session, *, clinic_id: int, email: str) -> models.Doctor:
    user = _make_user(db_session, email=email, role="doctor", clinic_id=clinic_id)
    doctor = models.Doctor(
        user_id=user.id,
        first_name="Doc",
        last_name="Test",
        specialty="gp",
        city="Conakry",
        phone="620000000",
        clinic_id=clinic_id,
    )
    db_session.add(doctor)
    db_session.commit()
    db_session.refresh(doctor)
    return doctor


def _token_for(user: User) -> str:
    return create_access_token(
        {"sub": user.email, "role": user.role, "user_id": user.id, "tv": int(user.token_version or 0)}
    )


def test_rt_whatsapp_webhook_rejects_unsigned(client, monkeypatch):
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)
    r = client.post(
        "/clinical/reminders/whatsapp/webhook",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "text": {"body": "ANNULER"},
                                        "context": {"appointment_id": 1},
                                        "from": "224620000000",
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )
    assert r.status_code == 403


def test_rt_whatsapp_webhook_accepts_valid_signature(client, db_session, monkeypatch):
    secret = "whatsapp-app-secret-for-redteam-tests"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    body = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "text": {"body": "HELLO"},
                                    "from": "224620000000",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    raw = json.dumps(body).encode("utf-8")
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    r = client.post(
        "/clinical/reminders/whatsapp/webhook",
        content=raw,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": f"sha256={sig}"},
    )
    assert r.status_code == 200
    assert r.json().get("status") in {"ignored", "no_appointment_context", "processed", "error"}


def test_rt_reminder_token_fail_closed(monkeypatch):
    monkeypatch.delenv("REMINDER_RESPOND_TOKEN", raising=False)
    assert verify_reminder_respond_token(1, "anything") is False


def test_rt_clinic_admin_cannot_access_other_clinic_appointment(client, db_session):
    c1 = _make_clinic(db_session, "C1")
    c2 = _make_clinic(db_session, "C2")
    admin = _make_user(db_session, email="ca1@test.gn", role="clinic_admin", clinic_id=c1.id)
    patient = models.Patient(first_name="P", last_name="T", age=30, gender="m", clinic_id=c2.id)
    db_session.add(patient)
    db_session.commit()
    doctor = _make_doctor(db_session, clinic_id=c2.id, email="doc-c2@test.gn")
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

    with pytest.raises(Exception):
        assert_appointment_access(db_session, appt, admin)

    token = _token_for(admin)
    r = client.patch(
        f"/rendezvous/{appt.id}",
        json={"status": "cancelled"},
        headers=_auth(token),
    )
    assert r.status_code in (403, 404)


def test_rt_admin_without_clinic_denied_appointment_access(client, db_session):
    c1 = _make_clinic(db_session, "C-null-admin")
    admin = _make_user(db_session, email="nulladmin@test.gn", role="admin", clinic_id=None)
    patient = models.Patient(first_name="P", last_name="N", age=20, gender="f", clinic_id=c1.id)
    db_session.add(patient)
    db_session.commit()
    doctor = _make_doctor(db_session, clinic_id=c1.id, email="doc-null@test.gn")
    appt = models.RendezVous(
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=c1.id,
        date=datetime.utcnow() + timedelta(days=2),
        duration_minutes=30,
        status="pending",
    )
    db_session.add(appt)
    db_session.commit()

    token = _token_for(admin)
    r = client.get(f"/appointments/{appt.id}", headers=_auth(token))
    assert r.status_code in (403, 404)


def test_rt_doctor_put_cross_clinic_denied(client, db_session):
    c1 = _make_clinic(db_session, "DocC1")
    c2 = _make_clinic(db_session, "DocC2")
    admin = _make_user(db_session, email="docadmin@test.gn", role="clinic_admin", clinic_id=c1.id)
    doctor = _make_doctor(db_session, clinic_id=c2.id, email="xdoc@test.gn")
    token = _token_for(admin)
    r = client.put(
        f"/doctors/{doctor.id}",
        json={"first_name": "Hacked"},
        headers=_auth(token),
    )
    assert r.status_code == 403


def test_rt_access_token_rejects_empty_jti(client, db_session, admin_user):
    # Craft a token with blank jti by encoding manually after create (bypass create_access_token)
    from jose import jwt
    from security import SECRET_KEY, ALGORITHM

    payload = {
        "sub": admin_user.email,
        "role": admin_user.role,
        "user_id": admin_user.id,
        "tv": 0,
        "jti": "",
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    bad = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    r = client.get("/auth/me", headers=_auth(bad))
    assert r.status_code == 401


def test_rt_create_access_token_never_empty_jti():
    tok = create_access_token({"sub": "a@b.c", "role": "patient", "jti": ""})
    payload = decode_access_token(tok)
    assert payload.get("jti")
    assert str(payload["jti"]).strip()


def test_rt_refresh_rotation_cas(db_session, admin_user):
    raw, _row = issue_refresh_token(db_session, user=admin_user)
    user, raw2, _new = rotate_refresh_token(db_session, raw_token=raw)
    assert user.id == admin_user.id
    assert raw2 != raw
    with pytest.raises(Exception):
        rotate_refresh_token(db_session, raw_token=raw)


def test_rt_update_rejects_path_traversal_and_unlisted_images(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIC_NODE_UPDATE_SECRET", "update-secret-redteam-32chars-min!!")
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "images").mkdir()
    evil = root / "images" / "payload.tar"
    evil.write_bytes(b"not-a-real-image")
    # Signed with empty files map — must fail because images exist
    claims = {"version": "9.9.9", "backup_required": False, "files": {}}
    (root / "manifest.json").write_text(json.dumps(claims), encoding="utf-8")
    from core.update_security import sign_manifest

    (root / "manifest.sig").write_text(sign_manifest(claims) + "\n", encoding="utf-8")
    with pytest.raises(UpdateSecurityError):
        load_and_verify_package(root)

    # Path traversal in files map
    claims2 = {
        "version": "9.9.10",
        "backup_required": False,
        "files": {"../outside.txt": "abc"},
    }
    (root / "manifest.json").write_text(json.dumps(claims2), encoding="utf-8")
    (root / "manifest.sig").write_text(sign_manifest(claims2) + "\n", encoding="utf-8")
    with pytest.raises(UpdateSecurityError, match="unsafe_path|path_escape"):
        load_and_verify_package(root)


def test_rt_update_signed_package_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIC_NODE_UPDATE_SECRET", "update-secret-redteam-32chars-min!!")
    root = tmp_path / "pkg2"
    (root / "images").mkdir(parents=True)
    (root / "images" / "backend.tar").write_bytes(b"image-bytes")
    pkg = write_signed_package(root, {"version": "1.2.3", "backup_required": False})
    loaded = load_and_verify_package(root)
    assert loaded.version == "1.2.3"
    assert "images/backend.tar" in pkg.claims["files"]


def test_rt_platform_owner_second_setup_closed(db_session):
    if platform_owner_exists(db_session):
        pytest.skip("owner already present")
    setup_first_platform_owner(
        db_session, email="owner1@redteam.gn", password="OwnerPass12!x"
    )
    with pytest.raises(PlatformOwnerSetupClosedError):
        setup_first_platform_owner(
            db_session, email="owner2@redteam.gn", password="OwnerPass12!y"
        )


def test_rt_mfa_required_role_hard_gate(client, db_session, monkeypatch):
    import services.mfa_service as mfa_service

    monkeypatch.setattr(mfa_service, "_MFA_REQUIRED", {"clinic_admin", "admin"})

    clinic = _make_clinic(db_session, "MFA Clinic")
    user = _make_user(
        db_session,
        email="mfa-admin@test.gn",
        role="clinic_admin",
        password="StrongPass12!",
        clinic_id=clinic.id,
    )
    user.mfa_enabled = False
    db_session.add(user)
    db_session.commit()
    r = client.post(
        "/auth/login-json",
        json={"email": user.email, "password": "StrongPass12!"},
    )
    assert r.status_code == 403
    detail = (r.json().get("detail") or "").upper()
    assert "MFA" in detail or r.headers.get("X-MFA-Enrollment-Required")


def test_rt_attachment_encryption_bypass_needs_attestation(monkeypatch):
    from core.settings import AppSettings, get_settings
    from cryptography.fernet import Fernet

    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DOMAIN", "api.example.com")
    monkeypatch.setenv("SECRET_KEY", "prod-jwt-secret-" + "A" * 32)
    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret-" + "A" * 32)
    monkeypatch.setenv("POSTGRES_PASSWORD", "StrongProductionDb!" + "Z" * 8)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://sante:StrongProductionDb!" + "Z" * 8 + "@db:5432/sante?sslmode=require",
    )
    monkeypatch.setenv("JITSI_APP_ID", "prod-jitsi-app")
    monkeypatch.setenv("JITSI_APP_SECRET", "jitsi-production-secret-" + "C" * 8)
    monkeypatch.setenv("ENABLE_PILOT_SEED", "false")
    monkeypatch.setenv("BYPASS_AVAILABILITY_VALIDATION", "false")
    monkeypatch.setenv("ENABLE_STARTUP_TEST_USER", "false")
    monkeypatch.setenv("ENABLE_STARTUP_SEED", "false")
    monkeypatch.setenv("ENABLE_DEMO_CLINIC_SEED", "false")
    monkeypatch.setenv("TRUSTED_PROXY_HOSTS", "127.0.0.1,backend")
    monkeypatch.setenv("REMINDER_RESPOND_TOKEN", "reminder-respond-token-" + "R" * 32)
    monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("REQUIRE_ATTACHMENT_ENCRYPTION", "false")
    monkeypatch.delenv("EMERGENCY_SECURITY_BYPASS_ATTESTATION", raising=False)
    with pytest.raises(RuntimeError, match="ATTACHMENT_ENCRYPTION_KEY"):
        AppSettings().enforce_production_boot()
    monkeypatch.setenv("ATTACHMENT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    AppSettings().enforce_production_boot()
    get_settings.cache_clear()
