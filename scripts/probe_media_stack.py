#!/usr/bin/env python3
"""Probe teleconsult stack: config, access, WebSocket (no WebRTC on platform backend)."""
from __future__ import annotations
import os

import asyncio
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
WS_BASE = "ws://127.0.0.1:8000"
AID = int(sys.argv[1]) if len(sys.argv) > 1 else 15


def http_json(method: str, path: str, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return e.code, json.loads(err)
        except json.JSONDecodeError:
            return e.code, {"raw": err}


def login(email: str, password: str) -> str:
    code, data = http_json("POST", "/auth/login-json", None, {"email": email, "password": password})
    return data["access_token"]


async def ws_probe_health():
    try:
        import websockets
    except ImportError:
        return "SKIP websockets package not installed"
    url = f"{WS_BASE}/ws/health"
    lines = []
    try:
        async with websockets.connect(url, open_timeout=5) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            lines.append(f"WS /ws/health recv: {msg}")
            await ws.send("ping")
            msg2 = await asyncio.wait_for(ws.recv(), timeout=5)
            lines.append(f"WS /ws/health ping->: {msg2}")
    except Exception as e:
        lines.append(f"WS /ws/health ERROR: {e}")
    return "\n".join(lines)


async def ws_probe_live(token: str):
    try:
        import websockets
    except ImportError:
        return "SKIP websockets package not installed"
    url = f"{WS_BASE}/ws/live"
    lines = []
    try:
        async with websockets.connect(url, open_timeout=5) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            lines.append(f"WS /ws/live recv: {msg}")
            if "auth_required" in msg:
                await ws.send(json.dumps({"type":"auth","token":token}))
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                lines.append(f"WS /ws/live auth->: {msg}")
            await ws.send(json.dumps({"type": "ping"}))
            msg2 = await asyncio.wait_for(ws.recv(), timeout=5)
            lines.append(f"WS /ws/live ping->: {msg2}")
    except Exception as e:
        lines.append(f"WS /ws/live ERROR: {e}")
    return "\n".join(lines)


def main():
    print("=== TELECONSULT MEDIA STACK PROBE ===\n")
    print("NOTE: La salle in-app (ConsultationRoom) n implemente PAS WebRTC/ICE/STUN.")
    print("      Le flux reel passe par Jitsi externe (meeting_link) si ouvert.\n")

    pat = login("test.patient@example.com", os.environ.get("PILOT_PATIENT_PASSWORD", ""))
    doc = login("dr.mamady@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", ""))

    code, cfg = http_json("GET", "/teleconsultation/config", pat)
    print(f"[HTTP {code}] GET /teleconsultation/config")
    print(json.dumps(cfg, indent=2, ensure_ascii=False))

    for role, token in [("patient", pat), ("medecin", doc)]:
        code, st = http_json("GET", f"/teleconsultation/appointments/{AID}/room-status", token)
        print(f"\n[HTTP {code}] room-status {role} RDV#{AID}")
        print(json.dumps(st, indent=2, ensure_ascii=False))
        code, acc = http_json("GET", f"/teleconsultation/appointments/{AID}/access", token)
        print(f"\n[HTTP {code}] access {role} RDV#{AID}")
        print(json.dumps(acc, indent=2, ensure_ascii=False))

    print("\n--- WebSocket backend (non utilise par ConsultationRoom.jsx) ---")
    print(asyncio.run(ws_probe_health()))
    print(asyncio.run(ws_probe_live(pat)))

    print("\n--- WebRTC / ICE / STUN cote plateforme ---")
    print("AUCUN endpoint backend pour ICE candidates ou STUN/TURN.")
    print("AUCUN RTCPeerConnection dans le frontend ConsultationRoom (stub UI).")
    print("Si Jitsi ouvert: WebRTC = meet.jit.si (hors logs backend).")


if __name__ == "__main__":
    main()
