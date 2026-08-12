"""Same-origin HttpOnly cookie session — complements cross-origin bearer regression."""

from __future__ import annotations

import models
from core.auth_cookie_config import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME
from core.provisioning_context import provisioning_channel
from security import hash_password


def _cookie_test_env(monkeypatch):
    """HttpOnly cookie path without Secure (TestClient is plain HTTP)."""
    monkeypatch.setenv("AUTH_JSON_TOKENS", "false")
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "false")
    monkeypatch.setenv("AUTH_COOKIE_SAMESITE", "lax")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)


def test_login_cookie_only_when_json_tokens_disabled(client, db_session, monkeypatch):
    _cookie_test_env(monkeypatch)
    from routers import auth as auth_router

    assert auth_router._json_tokens_enabled() is False

    with provisioning_channel("test_fixture"):
        user = models.User(
            email="cookie.recep@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

    response = client.post(
        "/auth/login-json",
        json={"email": "cookie.recep@test.gn", "password": "StrongPass12!"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("access_token") is None
    assert body.get("refresh_token") is None
    assert body.get("csrf_token")
    assert response.cookies.get(ACCESS_COOKIE_NAME)
    assert response.cookies.get(REFRESH_COOKIE_NAME)


def test_cookie_session_can_call_protected_route(client, db_session, monkeypatch):
    _cookie_test_env(monkeypatch)

    with provisioning_channel("test_fixture"):
        user = models.User(
            email="cookie.me@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

    login = client.post(
        "/auth/login-json",
        json={"email": "cookie.me@test.gn", "password": "StrongPass12!"},
    )
    assert login.status_code == 200, login.text
    assert client.cookies.get(ACCESS_COOKIE_NAME), dict(client.cookies)
    me = client.get("/auth/me")
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "cookie.me@test.gn"
