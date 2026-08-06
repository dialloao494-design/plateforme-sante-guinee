"""Regression: production SPA login must return bearer tokens in JSON.

Cookie-only auth breaks Safari/iOS when the frontend (Vercel) and API (Railway)
are cross-site. Clinic staff then see generic login failures and cannot print.
"""

from __future__ import annotations

import os

import models
from core.provisioning_context import provisioning_channel
from security import hash_password


def test_login_json_returns_bearer_tokens_in_production_env(client, db_session, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("AUTH_JSON_TOKENS", raising=False)

    # Re-import gate uses env at call time via os.getenv inside helper.
    from routers import auth as auth_router

    assert auth_router._json_tokens_enabled() is True

    with provisioning_channel("test_fixture"):
        user = models.User(
            email="spa.recep@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    response = client.post(
        "/auth/login-json",
        json={"email": "spa.recep@test.gn", "password": "StrongPass12!"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("access_token"), body
    assert body.get("refresh_token"), body
    assert body.get("csrf_token")


def test_staff_password_reset_clears_login_lockout(client, db_session, admin_user):
    from datetime import datetime, timedelta

    from security import create_access_token

    clinic = models.Clinic(name="Lock Clinic", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)

    with provisioning_channel("test_fixture"):
        staff = models.User(
            email="locked.recep@test.gn",
            hashed_password=hash_password("OldPassword12!"),
            role="receptionist",
            clinic_id=clinic.id,
            is_active=True,
            failed_login_attempts=8,
            locked_until=datetime.utcnow() + timedelta(minutes=30),
        )
        db_session.add(staff)
        db_session.flush()
        db_session.add(
            models.ClinicStaff(clinic_id=clinic.id, user_id=staff.id, is_active=True)
        )
        db_session.commit()
        db_session.refresh(staff)

    token = create_access_token(
        {
            "sub": admin_user.email,
            "user_id": admin_user.id,
            "user_role": admin_user.role,
            "role": admin_user.role,
        }
    )
    headers = {"Authorization": f"Bearer {token}"}

    reset = client.post(
        f"/platform/clinics/{clinic.id}/staff/{staff.id}/reset-password",
        json={"new_password": "AasmaRecep1!"},
        headers=headers,
    )
    assert reset.status_code == 200, reset.text

    db_session.refresh(staff)
    assert staff.failed_login_attempts == 0
    assert staff.locked_until is None

    login = client.post(
        "/auth/login-json",
        json={"email": "locked.recep@test.gn", "password": "AasmaRecep1!"},
    )
    assert login.status_code == 200, login.text
    assert login.json().get("access_token")


def test_json_tokens_can_be_explicitly_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_JSON_TOKENS", "false")
    from routers import auth as auth_router

    assert auth_router._json_tokens_enabled() is False
