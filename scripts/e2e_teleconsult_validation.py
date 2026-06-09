#!/usr/bin/env python3
"""E2E teleconsultation validation — creates RDV, checks doctor/patient API + room access."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8000"
PROXY = "http://127.0.0.1:5173"
DOCTOR_EMAIL = "dr.mamady@example.com"
DOCTOR_PASSWORD = "Doctor123!"
PATIENT_EMAIL = "test.patient@example.com"
PATIENT_PASSWORD = "Patient123!"
DOCTOR_ID = 4  # Dr Mamady Keïta in pilot seed


def req(
    method: str,
    path: str,
    token: str | None = None,
    body: dict | None = None,
    base: str = BASE,
    extra_headers: dict | None = None,
):
    url = f"{base}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            detail = json.loads(err)
        except json.JSONDecodeError:
            detail = err
        return e.code, detail


def login(email: str, password: str) -> str:
    code, data = req("POST", "/auth/login-json", body={"email": email, "password": password})
    if code != 200 or not data.get("access_token"):
        raise RuntimeError(f"Login failed {email}: {code} {data}")
    return data["access_token"]


def main() -> int:
    log: list[str] = []
    results: list[tuple[str, bool, str]] = []

    def record(step: str, ok: bool, detail: str = ""):
        results.append((step, ok, detail))
        mark = "OK" if ok else "FAIL"
        line = f"[{mark}] {step}" + (f" — {detail}" if detail else "")
        log.append(line)
        print(line)

    print("=== E2E TELECONSULTATION VALIDATION ===\n")

    pat_t = login(PATIENT_EMAIL, PATIENT_PASSWORD)
    doc_t = login(DOCTOR_EMAIL, DOCTOR_PASSWORD)
    record("Login patient + médecin", True)

    when = (datetime.now() + timedelta(minutes=8)).strftime("%Y-%m-%dT%H:%M:%S")
    payload = {
        "doctor_id": DOCTOR_ID,
        "date": when,
        "duration_minutes": 30,
        "consultation_type": "teleconsultation",
    }
    code, appt = req("POST", "/appointments/", pat_t, payload)
    if code not in (200, 201) or not isinstance(appt, dict) or not appt.get("id"):
        record("Créer RDV téléconsultation", False, f"HTTP {code} {appt}")
        _print_summary(results, log, None)
        return 1
    aid = appt["id"]
    record("Créer RDV téléconsultation", True, f"id={aid} date={when}")

    stub_headers = {}
    if os.getenv("PAYMENT_STUB_TOKEN"):
        stub_headers["X-Payment-Stub-Token"] = os.environ["PAYMENT_STUB_TOKEN"]
    code, paid = req(
        "POST",
        f"/payments/{aid}/confirm-payment",
        pat_t,
        {},
        extra_headers=stub_headers or None,
    )
    paid_ok = code == 200 and isinstance(paid, dict) and paid.get("status") == "confirmed"
    record("Paiement / confirmation", paid_ok, f"HTTP {code} status={paid.get('status') if isinstance(paid, dict) else paid}")

    code, doc_list = req("GET", "/appointments/", doc_t)
    doc_visible = code == 200 and any(a.get("id") == aid for a in (doc_list if isinstance(doc_list, list) else []))
    record("Visible côté médecin (GET /appointments/)", doc_visible, f"HTTP {code}")

    code, pat_list = req("GET", "/appointments/", pat_t)
    pat_visible = code == 200 and any(a.get("id") == aid for a in (pat_list if isinstance(pat_list, list) else []))
    record("Visible côté patient (GET /appointments/)", pat_visible, f"HTTP {code}")

    for role, token in [("patient", pat_t), ("médecin", doc_t)]:
        code, status = req("GET", f"/teleconsultation/appointments/{aid}/room-status", token)
        ok = code == 200 and isinstance(status, dict) and status.get("can_join") is True
        record(f"room-status {role}", ok, f"HTTP {code} reason={status.get('reason') if isinstance(status, dict) else status}")

        code, access = req("GET", f"/teleconsultation/appointments/{aid}/access", token)
        ok2 = code == 200 and isinstance(access, dict) and access.get("can_join") is True
        record(f"access {role} (API directe :8000)", ok2, f"HTTP {code}")

        code, status_p = req("GET", f"/teleconsultation/appointments/{aid}/room-status", token, base=PROXY)
        ok3 = code == 200 and isinstance(status_p, dict) and status_p.get("can_join") is True
        record(f"room-status {role} (proxy :5173)", ok3, f"HTTP {code}")

    code, refresh_html = req("GET", f"/consultation/{aid}", None, base=PROXY)
    # GET via urllib without Accept html may still get index - check vite separately below
    record("GET /consultation/{id} via proxy (non-HTML client)", code == 200, f"HTTP {code}")

    code, bad = req("GET", f"/consultation/{aid}", None, base=BASE)
    is_json_404 = code == 404 and isinstance(bad, dict) and "detail" in bad
    record("Port 8000 /consultation/{id} = 404 JSON attendu (pas utiliser pour refresh)", is_json_404, f"HTTP {code} body={bad}")

    _print_summary(results, log, aid, when)
    failed = sum(1 for _, ok, _ in results if not ok)
    return 1 if failed else 0


def _print_summary(results, log, aid, when=None):
    print("\n=== RÉSUMÉ ===")
    if aid:
        print(f"APPOINTMENT_ID={aid}")
        print(f"DOCTOR_URL=http://localhost:5173/consultation/{aid}")
        print(f"PATIENT_URL_LOCAL=http://localhost:5173/consultation/{aid}")
        print(f"PATIENT_URL_LAN=<IP_LAN>:5173/consultation/{aid}")
        print(f"RDV_DATE_LOCAL={when}")
    failed = [s for s, ok, _ in results if not ok]
    if failed:
        print(f"VERDICT=NO GO ({len(failed)} échec(s))")
    else:
        print("VERDICT=GO (API)")


if __name__ == "__main__":
    raise SystemExit(main())
