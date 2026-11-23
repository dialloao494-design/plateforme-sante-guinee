"""Synthetic regression coverage for enrollment, boot guards and private diagnostics."""
from datetime import datetime, timedelta
from unittest.mock import patch
import base64
import hashlib
import importlib.util
from pathlib import Path

import pyotp
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, inspect
from alembic.migration import MigrationContext
from alembic.operations import Operations

from core.settings import AppSettings, resolve_signing_key
from security import create_access_token
from services.auth_session_service import issue_refresh_token
from services.user_provisioning import register_public_user


@pytest.fixture(autouse=True)
def reset_enrollment_rate_limit():
    from core.limiter import limiter
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def mfa_user(db_session):
    import uuid
    user = register_public_user(db_session, email=f"mfa-{uuid.uuid4().hex}@example.test",
                                password="SyntheticPass456!", role="patient").user
    user.mfa_secret = pyotp.random_base32()
    user.mfa_enabled = True
    db_session.commit()
    return user


def headers(user):
    return {"Authorization": "Bearer " + create_access_token({
        "sub": user.email, "user_id": user.id, "user_role": user.role,
        "tv": user.token_version,
    })}


def proof(user):
    return {"password": "SyntheticPass456!", "current_code": pyotp.TOTP(user.mfa_secret).now()}


@pytest.mark.parametrize("bad", [{}, {"password": "incorrect"},
    {"password": "SyntheticPass456!"},
    {"password": "SyntheticPass456!", "current_code": "invalid"}])
def test_setup_cannot_replace_factor_with_session_alone(client, db_session, mfa_user, bad):
    old = mfa_user.mfa_secret
    r = client.post("/auth/mfa/setup", headers=headers(mfa_user), json=bad)
    assert r.status_code in (400, 422)
    db_session.refresh(mfa_user)
    assert mfa_user.mfa_secret == old and mfa_user.mfa_enabled
    assert mfa_user.mfa_pending_secret is None


def test_replacement_retains_factor_until_verified_and_revokes_sessions(client, db_session, mfa_user):
    old = mfa_user.mfa_secret
    old_headers = headers(mfa_user)
    raw_refresh, row = issue_refresh_token(db_session, user=mfa_user)
    setup = client.post("/auth/mfa/setup", headers=old_headers, json=proof(mfa_user))
    assert setup.status_code == 200
    pending = setup.json()["secret"]
    db_session.refresh(mfa_user)
    assert mfa_user.mfa_secret == old and mfa_user.mfa_enabled
    assert mfa_user.mfa_pending_secret == pending
    # An incomplete replacement continues to challenge using the original factor.
    from routers.auth import _enforce_mfa_on_login
    _enforce_mfa_on_login(mfa_user, pyotp.TOTP(old).now())
    for payload in ({"code": "invalid", **proof(mfa_user)},
                    {"code": pyotp.TOTP(pending).now()}):
        failed = client.post("/auth/mfa/confirm", headers=old_headers, json=payload)
        assert failed.status_code == 400
        db_session.refresh(mfa_user)
        assert mfa_user.mfa_secret == old
    confirmed = client.post("/auth/mfa/confirm", headers=old_headers,
        json={"code": pyotp.TOTP(pending).now(), **proof(mfa_user)})
    assert confirmed.status_code == 200
    db_session.refresh(mfa_user)
    db_session.refresh(row)
    assert mfa_user.mfa_secret == pending and mfa_user.mfa_enabled
    assert mfa_user.mfa_pending_secret is None
    assert row.revoked_at is not None
    assert client.get("/auth/me", headers=old_headers).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": raw_refresh}).status_code == 401
    fresh = {"Authorization": "Bearer " + confirmed.json()["access_token"]}
    assert client.get("/auth/me", headers=fresh).status_code == 200
    assert client.post("/auth/mfa/confirm", headers=fresh,
        json={"code": pyotp.TOTP(pending).now(), **proof(mfa_user)}).status_code == 400


def test_expired_pending_enrollment_does_not_change_active_factor(client, db_session, mfa_user):
    old = mfa_user.mfa_secret
    setup = client.post("/auth/mfa/setup", headers=headers(mfa_user), json=proof(mfa_user))
    mfa_user.mfa_pending_expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    r = client.post("/auth/mfa/confirm", headers=headers(mfa_user),
        json={"code": pyotp.TOTP(setup.json()["secret"]).now(), **proof(mfa_user)})
    assert r.status_code == 400
    db_session.refresh(mfa_user)
    assert mfa_user.mfa_secret == old and mfa_user.mfa_enabled


def test_first_enrollment_uses_pending_factor(client, db_session, mfa_user):
    mfa_user.mfa_enabled = False
    mfa_user.mfa_secret = None
    db_session.commit()
    h = headers(mfa_user)
    setup = client.post("/auth/mfa/setup", headers=h, json={"password": "SyntheticPass456!"})
    assert setup.status_code == 200
    db_session.refresh(mfa_user)
    assert not mfa_user.mfa_enabled and mfa_user.mfa_secret is None
    r = client.post("/auth/mfa/confirm", headers=h,
        json={"code": pyotp.TOTP(setup.json()["secret"]).now()})
    assert r.status_code == 200
    assert mfa_user.mfa_enabled


@pytest.mark.parametrize("name", ["RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT", "RENDER", "FLY_APP_NAME"])
@pytest.mark.parametrize("environment", [None, "", "prodution", "development"])
def test_hosted_environment_fails_closed(monkeypatch, name, environment):
    monkeypatch.setenv(name, "synthetic")
    if environment is None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
    else:
        monkeypatch.setenv("ENVIRONMENT", environment)
    with pytest.raises(RuntimeError, match="ENVIRONMENT"):
        AppSettings()


def test_conflicting_signing_aliases_fail_without_disclosing_keys(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "synthetic-primary-value")
    monkeypatch.setenv("JWT_SECRET", "synthetic-alias-value")
    with pytest.raises(RuntimeError, match="must match") as exc:
        AppSettings()
    assert "synthetic" not in str(exc.value)


@pytest.mark.parametrize("alias", ["SECRET_KEY", "JWT_SECRET"])
def test_signing_aliases_resolve_to_same_key(monkeypatch, alias):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv(alias, "synthetic-key")
    assert resolve_signing_key() == "synthetic-key"


def test_signer_uses_boot_settings_instance():
    import security
    from core.settings import get_settings
    assert security.SECRET_KEY == get_settings().signing_key


@pytest.mark.parametrize("path", ["/health", "/health/ready"])
def test_public_health_status_only(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert set(r.json()) == {"status"}


def test_unready_health_status_only(client):
    with patch("main.SessionLocal", side_effect=RuntimeError("synthetic-private-diagnostic")):
        r = client.get("/health/ready")
    assert r.status_code == 503
    assert r.json() == {"status": "not_ready"}


@pytest.mark.parametrize("path", ["/health/build", "/health/database", "/health/email"])
def test_diagnostics_require_platform_role(client, mfa_user, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers(mfa_user)).status_code == 403


def test_platform_diagnostics_remain_available(client, admin_user):
    with patch("main._database_fingerprint", return_value={"database_name": "synthetic"}):
        r = client.get("/health/database", headers=headers(admin_user))
    assert r.status_code == 200 and r.json()["database_name"] == "synthetic"


def test_pending_mfa_migration_preserves_active_factor():
    spec = importlib.util.spec_from_file_location("pending_mfa_migration",
        Path(__file__).resolve().parents[1] / "alembic/versions/20261123_0041_pending_mfa.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    from sqlalchemy import text
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, mfa_secret VARCHAR, mfa_enabled BOOLEAN)"))
        conn.execute(text("INSERT INTO users VALUES (1, 'synthetic-factor', 1)"))
        with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
            migration.upgrade()
            migration.upgrade()
            assert {"mfa_pending_secret", "mfa_pending_expires_at"} <= {c["name"] for c in inspect(conn).get_columns("users")}
            assert conn.execute(text("SELECT mfa_secret, mfa_enabled FROM users")).one() == ("synthetic-factor", 1)
            migration.downgrade()
            assert conn.execute(text("SELECT mfa_secret, mfa_enabled FROM users")).one() == ("synthetic-factor", 1)


def test_derived_attachment_key_keeps_existing_ciphertext_readable(monkeypatch):
    from core.attachment_encryption import decrypt_blob, reset_encryption_cache
    from tests.test_production_boot_guard import _apply_valid_production_env
    _apply_valid_production_env(monkeypatch)
    monkeypatch.delenv("ATTACHMENT_ENCRYPTION_KEY", raising=False)
    settings = AppSettings()
    legacy_key = base64.urlsafe_b64encode(hashlib.sha256(
        b"sante-guinee-attachment-v1:" + settings.signing_key.encode()).digest())
    ciphertext = b"\x00ATTENC\x01" + Fernet(legacy_key).encrypt(b"synthetic attachment")
    try:
        settings.enforce_production_boot()
        reset_encryption_cache()
        assert decrypt_blob(ciphertext) == b"synthetic attachment"
        assert decrypt_blob(b"synthetic legacy plaintext") == b"synthetic legacy plaintext"
    finally:
        reset_encryption_cache()


def test_disable_cancels_pending_enrollment(client, db_session, mfa_user):
    h = headers(mfa_user)
    setup = client.post("/auth/mfa/setup", headers=h, json=proof(mfa_user))
    assert setup.status_code == 200
    r = client.post("/auth/mfa/disable", headers=h, json={
        "password": "SyntheticPass456!", "code": pyotp.TOTP(mfa_user.mfa_secret).now()})
    assert r.status_code == 200
    db_session.refresh(mfa_user)
    assert mfa_user.mfa_pending_secret is None and not mfa_user.mfa_enabled
    assert client.post("/auth/mfa/confirm", headers=h,
        json={"code": pyotp.TOTP(setup.json()["secret"]).now()}).status_code == 400


def test_enrollment_attempts_are_rate_limited(client, mfa_user):
    h = headers(mfa_user)
    for _ in range(5):
        assert client.post("/auth/mfa/setup", headers=h,
            json={"password": "incorrect"}).status_code == 400
    assert client.post("/auth/mfa/setup", headers=h, json=proof(mfa_user)).status_code == 429


def test_refresh_reloads_revocation_after_loading_user(db_session, mfa_user):
    """A stale ORM token must not survive a committed security revocation."""
    from sqlalchemy import update
    from fastapi import HTTPException
    from models.refresh_token import RefreshToken
    from services.auth_session_service import rotate_refresh_token
    raw, row = issue_refresh_token(db_session, user=mfa_user)
    # Simulate another transaction's committed revocation, leaving this request's
    # identity-map row stale. PostgreSQL lock scheduling is a separate staging check.
    db_session.execute(update(RefreshToken).where(RefreshToken.id == row.id).values(
        revoked_at=datetime.utcnow()), execution_options={"synchronize_session": False})
    db_session.flush()
    assert row.revoked_at is None
    with pytest.raises(HTTPException) as exc:
        rotate_refresh_token(db_session, raw_token=raw)
    assert exc.value.status_code == 401
    assert db_session.query(RefreshToken).filter(RefreshToken.user_id == mfa_user.id).count() == 1
