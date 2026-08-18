"""
WebSocket endpoints — connectivity probe and authenticated live channel.

Clients connect via nginx: wss://<domain>/api/ws/<path>

Authentication (never via query string — leaks in logs/referrers):
  1. HttpOnly access cookie on the handshake (preferred when same-origin), or
  2. First message after connect: {"type":"auth","token":"<jwt>"} within a short timeout.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jwt import PyJWTError

from core.auth_cookie_config import ACCESS_COOKIE_NAME
from core.roles import roles_equivalent
from database import SessionLocal
from models.user import User
from security import decode_access_token
from services.auth_session_service import is_access_jti_denied

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])

WS_AUTH_TIMEOUT_SECONDS = 5.0
WS_HEARTBEAT_TIMEOUT_SECONDS = 55.0


def _decode_ws_token(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if payload.get("user_id") is None or not str(payload.get("jti") or "").strip():
            return None
        return payload
    except PyJWTError:
        return None
    except Exception:
        return None


def _validate_ws_identity(payload: dict | None) -> bool:
    """Apply the same account/session invalidation controls as HTTP auth."""
    if not payload:
        return False
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == payload.get("user_id")).first()
        if user is None or user.is_active is False or bool(user.must_change_password):
            return False
        if is_access_jti_denied(db, jti=payload.get("jti")):
            return False
        token_role = payload.get("user_role") or payload.get("role")
        if token_role and not roles_equivalent(token_role, user.role):
            return False
        if int(payload.get("session_version", 0)) != int(user.session_version or 0):
            return False
        token_version = payload.get("tv", payload.get("token_version"))
        user_token_version = int(user.token_version or 0)
        if token_version is None:
            return user_token_version == 0
        return int(token_version) == user_token_version
    except (TypeError, ValueError):
        return False
    except Exception:
        logger.exception("WS identity validation failed closed")
        return False
    finally:
        db.close()


def _token_from_cookie(websocket: WebSocket) -> str | None:
    raw = websocket.cookies.get(ACCESS_COOKIE_NAME)
    return (raw or "").strip() or None


def _reject_query_token(websocket: WebSocket) -> bool:
    """Return True when a forbidden ?token= query param is present."""
    if websocket.query_params.get("token"):
        logger.warning("WS auth rejected: JWT in query string is not permitted")
        return True
    return False


async def _authenticate_live_channel(websocket: WebSocket) -> dict | None:
    """
    Resolve JWT from cookie (handshake) or first auth message after accept.
    Returns decoded payload or None when authentication fails.
    """
    cookie_token = _token_from_cookie(websocket)
    cookie_payload = _decode_ws_token(cookie_token)
    if cookie_payload and _validate_ws_identity(cookie_payload):
        return cookie_payload

    await websocket.accept()
    try:
        await websocket.send_json({"type": "auth_required"})
        raw = await asyncio.wait_for(
            websocket.receive_text(),
            timeout=WS_AUTH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.info("WS live auth timeout — no credentials within %.0fs", WS_AUTH_TIMEOUT_SECONDS)
        await websocket.close(code=4401)
        return None
    except WebSocketDisconnect:
        return None

    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await websocket.close(code=4401)
        return None

    if msg.get("type") != "auth":
        await websocket.close(code=4401)
        return None

    token = (msg.get("token") or "").strip()
    payload = _decode_ws_token(token)
    if not payload or not _validate_ws_identity(payload):
        await websocket.close(code=4401)
        return None
    return payload


@router.get("/status")
def ws_http_status():
    """HTTP probe — proves the WS router is mounted even when upgrades fail at the edge."""
    return {
        "status": "ok",
        "websocket_paths": ["/ws/health", "/ws/live"],
        "auth": "cookie_or_first_message",
        "query_token": "rejected",
    }


@router.websocket("/health")
async def ws_health(websocket: WebSocket):
    """Public ping/pong — validates nginx WebSocket proxy without auth."""
    await websocket.accept()
    try:
        await websocket.send_json({"type": "ready", "service": "plateforme-sante-api"})
        while True:
            raw = await websocket.receive_text()
            if raw.strip().lower() in ("ping", '{"type":"ping"}'):
                await websocket.send_json({"type": "pong"})
            else:
                await websocket.send_json({"type": "echo", "received": raw[:200]})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS health closed: %s", exc)


@router.websocket("/live")
async def ws_live(websocket: WebSocket):
    """
    Authenticated channel for real-time notifications.

    Auth via HttpOnly cookie on handshake or first message
    ``{"type":"auth","token":"<access_jwt>"}`` (5s timeout).
    Query-string ``?token=`` is rejected.
    """
    if _reject_query_token(websocket):
        # Must accept before close so proxies don't collapse the denial into a bare 404.
        await websocket.accept()
        await websocket.send_json({"type": "error", "detail": "query_token_forbidden"})
        await websocket.close(code=4401)
        return

    cookie_payload = _decode_ws_token(_token_from_cookie(websocket))
    if cookie_payload and _validate_ws_identity(cookie_payload):
        await websocket.accept()
        payload = cookie_payload
    else:
        payload = await _authenticate_live_channel(websocket)
        if not payload:
            return

    user_id = payload.get("user_id")
    try:
        await websocket.send_json(
            {"type": "connected", "user_id": user_id, "message": "live channel ready"}
        )
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=WS_HEARTBEAT_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                if not _validate_ws_identity(payload):
                    await websocket.close(code=4401)
                    return
                await websocket.send_json({"type": "heartbeat"})
                continue
            if not _validate_ws_identity(payload):
                await websocket.close(code=4401)
                return
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                msg = {"type": "unknown", "raw": raw[:100]}
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong", "user_id": user_id})
            else:
                await websocket.send_json({"type": "ack", "received": msg.get("type", "message")})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS live closed user_id=%s: %s", user_id, exc)
