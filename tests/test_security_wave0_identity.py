"""Security Wave 0 — Authentication & Identity hardening tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import models
from core.password_policy import validate_password
from core.rbac import ROLE_PERMISSIONS, Permission, has_permission
from core.roles import ALL_ROLES, effective_role
from models.refresh_token import RefreshToken
from models.user import User
from security import create_access_token, hash_password, decode_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from services.mfa_service import generate_mfa_secret, verify_totp
import pyotp


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_password_policy_requires_12_and_complexity():
    try:
        validate_password("Short1!")
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        validate_password("alllowercase12")
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        validate_password("password123")
        assert False, "expected common password rejection"
    except ValueError:
        pass
    assert validate_password("StrongPass12!") is True


def test_rbac_matrix_covers_every_role():
    missing = sorted(ALL_ROLES - set(ROLE_PERMISSIONS.keys()) - {"admin"})
    # admin is legacy alias; clinic_admin is canonical — both must be present
    assert "admin" in ROLE_PERMISSIONS
    assert "clinic_admin" in ROLE_PERMISSIONS
    assert "nurse" in ROLE_PERMISSIONS
    assert "pev_agent" in ROLE_PERMISSIONS
    assert "patient" in ROLE_PERMISSIONS
    assert not (ALL_ROLES - set(ROLE_PERMISSIONS.keys())), (
        f"ROLE_PERMISSIONS missing roles: {ALL_ROLES - set(ROLE_PERMISSIONS.keys())}"
    )


def test_login_issues_refresh_and_short_access_ttl(client, admin_user):
    r = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("access_token")
    assert body.get("refresh_token")
    assert body.get("expires_in") == ACCESS_TOKEN_EXPIRE_MINUTES * 60
    payload = decode_access_token(body["access_token"])
    assert payload.get("jti")
    assert payload.get("iat") is not None
    assert "tv" in payload or payload.get("tv") == 0


def test_refresh_rotates_and_reuse_revokes(client, admin_user, db_session):
    login = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    ).json()
    refresh1 = login["refresh_token"]
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert r2.status_code == 200, r2.text
    refresh2 = r2.json()["refresh_token"]
    assert refresh2 != refresh1

    # Reuse of rotated token must fail and revoke family
    reuse = client.post("/auth/refresh", json={"refresh_token": refresh1})
    assert reuse.status_code == 401
    reuse2 = client.post("/auth/refresh", json={"refresh_token": refresh2})
    assert reuse2.status_code == 401


def test_logout_denylists_access_token(client, admin_user):
    login = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    ).json()
    access = login["access_token"]
    refresh = login["refresh_token"]
    me = client.get("/auth/me", headers=_headers(access))
    assert me.status_code == 200
    out = client.post("/auth/logout", json={"refresh_token": refresh}, headers=_headers(access))
    assert out.status_code == 200
    me2 = client.get("/auth/me", headers=_headers(access))
    assert me2.status_code == 401


def test_must_change_password_blocks_clinical_api(client, db_session, admin_user):
    admin_user.must_change_password = True
    db_session.add(admin_user)
    db_session.commit()

    login = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    ).json()
    access = login["access_token"]
    assert login.get("must_change_password") is True

    me = client.get("/auth/me", headers=_headers(access))
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    blocked = client.get("/platform/clinics", headers=_headers(access))
    assert blocked.status_code == 403
    assert "password" in blocked.json()["detail"].lower()

    # Clear for other tests
    admin_user.must_change_password = False
    db_session.add(admin_user)
    db_session.commit()


def test_change_password_revokes_old_token_and_issues_new(client, db_session, admin_user):
    login = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    ).json()
    old_access = login["access_token"]
    r = client.post(
        "/auth/change-password",
        json={"current_password": "AdminPass1", "new_password": "NewerSecure99!"},
        headers=_headers(old_access),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("access_token")
    assert body.get("refresh_token")

    old_me = client.get("/auth/me", headers=_headers(old_access))
    assert old_me.status_code == 401

    new_me = client.get("/auth/me", headers=_headers(body["access_token"]))
    assert new_me.status_code == 200

    # restore password for other tests
    admin_user.hashed_password = hash_password("AdminPass1")
    admin_user.token_version = 0
    admin_user.must_change_password = False
    db_session.add(admin_user)
    db_session.commit()


def test_account_lockout_after_failures(client, db_session, admin_user):
    admin_user.failed_login_attempts = 0
    admin_user.locked_until = None
    db_session.add(admin_user)
    db_session.commit()

    # Soft throttle begins at LOGIN_SOFT_LOCK_START (default 3)
    statuses = []
    for _ in range(3):
        r = client.post(
            "/auth/login-json",
            json={"email": admin_user.email, "password": "WrongPass999!"},
        )
        statuses.append(r.status_code)
    assert 429 in statuses
    db_session.refresh(admin_user)
    assert int(admin_user.failed_login_attempts or 0) >= 3

    # Force hard lock threshold
    admin_user.failed_login_attempts = 4
    admin_user.locked_until = None
    db_session.add(admin_user)
    db_session.commit()
    hard = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "WrongPass999!"},
    )
    assert hard.status_code == 429
    db_session.refresh(admin_user)
    assert admin_user.locked_until is not None

    locked = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    )
    assert locked.status_code == 429

    admin_user.failed_login_attempts = 0
    admin_user.locked_until = None
    db_session.add(admin_user)
    db_session.commit()


def test_token_version_mismatch_rejected(client, db_session, admin_user):
    token = create_access_token(
        {
            "sub": admin_user.email,
            "user_id": admin_user.id,
            "user_role": admin_user.role,
            "role": admin_user.role,
            "tv": 0,
        }
    )
    admin_user.token_version = 3
    db_session.add(admin_user)
    db_session.commit()
    r = client.get("/auth/me", headers=_headers(token))
    assert r.status_code == 401
    admin_user.token_version = 0
    db_session.add(admin_user)
    db_session.commit()


def test_mfa_challenge_when_enabled(client, db_session, admin_user):
    admin_user.failed_login_attempts = 0
    admin_user.locked_until = None
    secret = generate_mfa_secret()
    admin_user.mfa_secret = secret
    admin_user.mfa_enabled = True
    db_session.add(admin_user)
    db_session.commit()

    denied = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    )
    assert denied.status_code == 401
    assert "MFA" in denied.json()["detail"]

    code = pyotp.TOTP(secret).now()
    ok = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1", "mfa_code": code},
    )
    assert ok.status_code == 200, ok.text

    admin_user.mfa_enabled = False
    admin_user.mfa_secret = None
    admin_user.failed_login_attempts = 0
    admin_user.locked_until = None
    db_session.add(admin_user)
    db_session.commit()


def test_staff_provisioning_sets_must_change_password(client, db_session, admin_headers):
    clinic = models.Clinic(name="Wave0 Clinic", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)

    # Prefer clinical staff create endpoint if present
    r = client.post(
        "/clinical/staff",
        json={
            "email": "nurse.wave0@clinic.test",
            "password": "TempStaffPass99!",
            "role": "nurse",
            "clinic_id": clinic.id,
        },
        headers=admin_headers,
    )
    if r.status_code in (404, 405):
        # Fallback: use user_provisioning directly
        from core.provisioning_context import provisioning_channel
        from services.user_provisioning import create_staff_user

        with provisioning_channel("test_fixture"):
            provisioned = create_staff_user(
                db_session,
                email="nurse.wave0@clinic.test",
                password="TempStaffPass99!",
                role="nurse",
                clinic_id=clinic.id,
            )
        assert provisioned.user.must_change_password is True
        return

    assert r.status_code in (200, 201), r.text
    user = db_session.query(User).filter(User.email == "nurse.wave0@clinic.test").first()
    assert user is not None
    assert user.must_change_password is True


def test_nurse_has_permissions():
    class _U:
        role = "nurse"

    assert has_permission(_U(), Permission.PATIENT_JOURNEY)
    assert has_permission(_U(), Permission.CLINIC_OPERATIONS)
