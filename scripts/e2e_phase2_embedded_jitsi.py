#!/usr/bin/env python3
"""Phase 2 validation — embed access payload + API gates."""
from __future__ import annotations

import json
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

BASE = "http://127.0.0.1:8000"
PROXY = "http://127.0.0.1:5173"
TUNNEL = "https://playing-caution-divisions-advisors.trycloudflare.com"
DOCTOR_ID = 4
ROOT = Path(__file__).resolve().parents[1]


def req(method, path, token=None, body=None, base=BASE, extra_headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if extra_headers:
        h.update(extra_headers)
    r = urllib.request.Request(f"{base}{path}", data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return e.code, json.loads(err)
        except json.JSONDecodeError:
            return e.code, {"raw": err}


def login(email, password):
    _, d = req("POST", "/auth/login-json", None, {"email": email, "password": password})
    return d["access_token"]


def ensure_joinable_appointment() -> int:
    """Create or refresh a teleconsultation RDV in the join window."""
    pat = login("test.patient@example.com", "Patient123!")
    when = (datetime.now() + timedelta(minutes=8)).strftime("%Y-%m-%dT%H:%M:%S")
    code, appt = req(
        "POST",
        "/appointments/",
        pat,
        {
            "doctor_id": DOCTOR_ID,
            "date": when,
            "duration_minutes": 30,
            "consultation_type": "teleconsultation",
        },
    )
    if code in (200, 201) and appt.get("id"):
        aid = appt["id"]
        import os

        stub_headers = {}
        if os.getenv("PAYMENT_STUB_TOKEN"):
            stub_headers["X-Payment-Stub-Token"] = os.environ["PAYMENT_STUB_TOKEN"]
        req("POST", f"/payments/{aid}/confirm-payment", pat, {}, extra_headers=stub_headers or None)
        return aid

    # fallback: bump latest teleconsult RDV into window
    db = sqlite3.connect(ROOT / "sante.db")
    row = db.execute(
        "SELECT id FROM rendezvous WHERE consultation_type='teleconsultation' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    db.close()
    if not row:
        raise RuntimeError("No teleconsult appointment available")
    aid = row[0]
    new_date = (datetime.now() + timedelta(minutes=8)).strftime("%Y-%m-%d %H:%M:%S.%f")
    db = sqlite3.connect(ROOT / "sante.db")
    db.execute("UPDATE rendezvous SET date=?, status='confirmed', payment_status='paid' WHERE id=?", (new_date, aid))
    db.commit()
    db.close()
    return aid


def main():
    checks = []
    print("=== PHASE 2 EMBEDDED JITSI VALIDATION ===\n")

    try:
        urllib.request.urlopen(f"{BASE}/health", timeout=5)
        checks.append(("Backend health", True, "200"))
    except Exception as e:
        checks.append(("Backend health", False, str(e)))
        print("Backend not reachable — start uvicorn first.")
        return 1

    aid = ensure_joinable_appointment()
    pat = login("test.patient@example.com", "Patient123!")
    doc = login("dr.mamady@example.com", "Doctor123!")

    for role, token in [("patient", pat), ("doctor", doc)]:
        code, acc = req("GET", f"/teleconsultation/appointments/{aid}/access", token)
        ok = (
            code == 200
            and acc.get("embed_mode") == "jitsi_iframe"
            and acc.get("provider") == "jitsi"
            and acc.get("room_name", "").startswith(f"sante-gn-{aid}-")
            and acc.get("jitsi_domain")
            and acc.get("display_name")
            and acc.get("room_name") in (acc.get("meeting_url") or "")
        )
        checks.append((f"access embed {role}", ok, f"HTTP {code} room={acc.get('room_name')}"))
        print(f"[{'OK' if ok else 'FAIL'}] access {role}: {acc.get('room_name')} domain={acc.get('jitsi_domain')}")

    code, cfg = req("GET", "/teleconsultation/config", pat)
    checks.append(("config provider jitsi", code == 200 and cfg.get("provider") == "jitsi", str(cfg)))

    for base, label in [(PROXY, ":5173"), (TUNNEL, "tunnel")]:
        url = f"{base}/consultation/{aid}"
        with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as resp:
            body = resp.read(300).decode()
        ok = "<!doctype html>" in body.lower()
        checks.append((f"SPA refresh {label}", ok, f"HTTP {resp.status}"))
        print(f"[{'OK' if ok else 'FAIL'}] SPA {label}/consultation/{aid}")

    # RBAC negative: wrong patient cannot access
    # (skip if only one patient in seed)

    failed = [n for n, ok, _ in checks if not ok]
    print("\n=== LIVRABLES TEST ===")
    print(f"APPOINTMENT_ID={aid}")
    print(f"DOCTOR_URL=http://localhost:5173/consultation/{aid}")
    print(f"PATIENT_URL_4G={TUNNEL}/consultation/{aid}")
    print(f"\nVERDICT={'GO' if not failed else 'NO GO'}")
    if failed:
        print("Failed:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
