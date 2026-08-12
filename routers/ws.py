"""WebSocket endpoints."""
from __future__ import annotations
import asyncio, json, logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.auth_cookie_config import ACCESS_COOKIE_NAME
from security import decode_access_token
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])
AUTH_TIMEOUT = 5.0
HB_TIMEOUT = 55.0

def _decode(token):
    if not token: return None
    try:
        p = decode_access_token(token)
        return p if p.get("user_id") is not None else None
    except Exception:
        return None

async def _auth_msg(ws):
    await ws.accept()
    try:
        await ws.send_json({"type": "auth_required"})
        raw = await asyncio.wait_for(ws.receive_text(), timeout=AUTH_TIMEOUT)
    except Exception:
        await ws.close(code=4401); return None
    try: msg = json.loads(raw)
    except json.JSONDecodeError:
        await ws.close(code=4401); return None
    if msg.get("type") != "auth": await ws.close(code=4401); return None
    p = _decode((msg.get("token") or "").strip())
    if not p: await ws.close(code=4401)
    return p

@router.websocket("/health")
async def ws_health(ws: WebSocket):
    await ws.accept()
    try:
        await ws.send_json({"type": "ready", "service": "plateforme-sante-api"})
        while True:
            raw = await ws.receive_text()
            await ws.send_json({"type": "pong"} if raw.strip().lower() in ("ping", '{"type":"ping"}') else {"type": "echo", "received": raw[:200]})
    except WebSocketDisconnect: pass

@router.websocket("/live")
async def ws_live(ws: WebSocket):
    if ws.query_params.get("token"):
        logger.warning("WS query token rejected"); await ws.close(code=4401); return
    cookie = _decode((ws.cookies.get(ACCESS_COOKIE_NAME) or "").strip() or None)
    if cookie:
        await ws.accept(); payload = cookie
    else:
        payload = await _auth_msg(ws)
        if not payload: return
    uid = payload.get("user_id")
    try:
        await ws.send_json({"type": "connected", "user_id": uid, "message": "live channel ready"})
        while True:
            try: raw = await asyncio.wait_for(ws.receive_text(), timeout=HB_TIMEOUT)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "heartbeat"}); continue
            try: msg = json.loads(raw)
            except json.JSONDecodeError: msg = {"type": "unknown"}
            await ws.send_json({"type": "pong", "user_id": uid} if msg.get("type") == "ping" else {"type": "ack", "received": msg.get("type", "message")})
    except WebSocketDisconnect: pass
