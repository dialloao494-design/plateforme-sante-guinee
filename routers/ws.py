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
from jose import JWTError

from core.auth_cookie_config import ACCESS_COOKIE_NAME
from security import decode_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])

WS_AUTH_TIMEOUT_SECONDS = 5.0
WS_HEARTBEAT_TIMEOUT_SECONDS = 55.0


def _decode_ws_token(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        if payload.get("user_id") is None:
            return None
        return payload
    except JWTError:
        return None
    except Exception:
        return None


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
    if cookie_payload:
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
    if not payload:
        await websocket.close(code=4401)
        return None
    return payload


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
        await websocket.close(code=4401)
        return

    cookie_payload = _decode_ws_token(_token_from_cookie(websocket))
    if cookie_payload:
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
                await websocket.send_json({"type": "heartbeat"})
                continue
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
