"""WebSocket authentication — cookie / post-connect auth; reject query tokens."""

from __future__ import annotations

import json
import uuid

import pytest
from core.auth_cookie_config import ACCESS_COOKIE_NAME
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password

import models


def _make_user(db_session):
    with provisioning_channel("test_fixture"):
        user = models.User(
            email=f"ws.user.{uuid.uuid4().hex[:10]}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def _token_for(user) -> str:
    return create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
        }
    )


def test_ws_health_is_public(client):
    with client.websocket_connect("/ws/health") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        ws.send_text("ping")
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_ws_live_rejects_query_token(client, db_session):
    user = _make_user(db_session)
    token = _token_for(user)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/live?token={token}") as ws:
            ws.receive_json()


def test_ws_live_accepts_cookie_auth(client, db_session):
    user = _make_user(db_session)
    token = _token_for(user)
    client.cookies.set(ACCESS_COOKIE_NAME, token)
    with client.websocket_connect("/ws/live") as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"
        assert connected["user_id"] == user.id
        ws.send_text(json.dumps({"type": "ping"}))
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_ws_live_accepts_post_connect_auth_message(client, db_session):
    user = _make_user(db_session)
    token = _token_for(user)
    with client.websocket_connect("/ws/live") as ws:
        challenge = ws.receive_json()
        assert challenge["type"] == "auth_required"
        ws.send_text(json.dumps({"type": "auth", "token": token}))
        connected = ws.receive_json()
        assert connected["type"] == "connected"
        assert connected["user_id"] == user.id


def test_ws_live_rejects_invalid_post_connect_token(client):
    with client.websocket_connect("/ws/live") as ws:
        ws.receive_json()
        ws.send_text(json.dumps({"type": "auth", "token": "not-a-valid-jwt"}))
