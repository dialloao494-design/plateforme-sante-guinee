"""
WebSocket endpoints — connectivity probe and authenticated live channel.

Clients connect via nginx: wss://<domain>/api/ws/<path>
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from security import ALGORITHM, SECRET_KEY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])


def _decode_ws_token(token: str | None) -> dict | None:
    if not token or not SECRET_KEY:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("user_id") is None:
            return None
        return payload
    except JWTError:
        return None


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
    Authenticated channel for future real-time notifications.
    Pass JWT as query: /api/ws/live?token=<access_token>
    """
    token = websocket.query_params.get("token")
    payload = _decode_ws_token(token)
    if not payload:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    user_id = payload.get("user_id")
    try:
        await websocket.send_json(
            {"type": "connected", "user_id": user_id, "message": "live channel ready"}
        )
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=55.0)
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
