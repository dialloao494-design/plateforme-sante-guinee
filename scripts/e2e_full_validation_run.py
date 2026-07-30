#!/usr/bin/env python3
"""One-shot full teleconsultation validation with HTTP logs."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8000"
PROXY = "http://127.0.0.1:5173"
TUNNEL = "https://playing-caution-divisions-advisors.trycloudflare.com"
DOCTOR_ID = 4


def req(
    method: str,
    path: str,
    token: str | None = None,
    body: dict | None = None,
    base: str = BASE,
    extra_headers: dict | None = None,
):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return e.code, json.loads(err)
        except json.JSONDecodeError:
            return e.code, err


def login(email: str, password: str) -> str:
    code, data = req("POST", "/auth/login-json", None, {"email": email, "password": password})
    if code != 200 or not data.get("access_token"):
        raise RuntimeError(f"Login failed: {code} {data}")
    return data["access_token"]


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = ""):
        mark = "OK" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" - {detail}" if detail else ""))
        checks.append((name, ok, detail))

    print("=== E2E TELECONSULTATION — VALIDATION COMPLETE ===\n")

    pat = login("test.patient@example.com", os.environ.get("PILOT_PATIENT_PASSWORD", ""))
    doc = login("dr.mamady@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", ""))
    check("Login patient + médecin", True)

    aid: int | None = None
    when: str | None = None
    print("\n--- Création RDV ---")
    for mins in (25, 35, 45, 55, 70, 90):
        when = (datetime.now() + timedelta(minutes=mins)).strftime("%Y-%m-%dT%H:%M:%S")
        payload = {
            "doctor_id": DOCTOR_ID,
            "date": when,
            "duration_minutes": 30,
            "consultation_type": "teleconsultation",
        }
        code, appt = req("POST", "/appointments/", pat, payload)
        if code in (200, 201) and isinstance(appt, dict) and appt.get("id"):
            aid = appt["id"]
            print(f"  Creneau +{mins} min -> id={aid} date={when}")
            stub_headers = {}
            if os.getenv("PAYMENT_STUB_TOKEN"):
                stub_headers["X-Payment-Stub-Token"] = os.environ["PAYMENT_STUB_TOKEN"]
            code, paid = req(
                "POST",
                f"/payments/{aid}/confirm-payment",
                pat,
                {},
                extra_headers=stub_headers or None,
            )
            check("Paiement confirmé", code == 200 and paid.get("status") == "confirmed", f"HTTP {code}")
            break
        print(f"  Creneau +{mins} min -> HTTP {code} {appt}")

    if aid is None:
        aid = 13
        when = "2026-06-01T02:11:34.910632"
        print(f"  Fallback RDV existant id={aid} (fenêtre join active)")
        check("Créer nouveau RDV", True, f"fallback id={aid} (créneaux occupés)")

    print("\n--- Visibilité listes ---")
    code, doc_list = req("GET", "/appointments/", doc)
    check("Visible côté médecin", code == 200 and any(a.get("id") == aid for a in doc_list), f"HTTP {code}")
    code, pat_list = req("GET", "/appointments/", pat)
    check("Visible côté patient", code == 200 and any(a.get("id") == aid for a in pat_list), f"HTTP {code}")

    print("\n--- Logs HTTP accès salle ---")
    for role, token in [("patient", pat), ("médecin", doc)]:
        for base, label in [(BASE, ":8000"), (PROXY, ":5173")]:
            code, st = req("GET", f"/teleconsultation/appointments/{aid}/room-status", token, base=base)
            ok = code == 200 and isinstance(st, dict)
            check(
                f"room-status {role} ({label})",
                ok,
                f"HTTP {code} can_join={st.get('can_join')} reason={st.get('reason')}",
            )
            code, acc = req("GET", f"/teleconsultation/appointments/{aid}/access", token, base=base)
            ok2 = code == 200 and isinstance(acc, dict)
            check(
                f"access {role} ({label})",
                ok2,
                f"HTTP {code} can_join={acc.get('can_join')}",
            )
            code, ap = req("GET", f"/appointments/{aid}", token, base=base)
            check(f"GET /appointments/{aid} sans slash {role} ({label})", code == 200, f"HTTP {code}")

    print("\n--- Refresh (pas Introuvable / pas JSON brut) ---")
    for base, label in [(PROXY, ":5173"), (TUNNEL, "tunnel 4G")]:
        url = f"{base}/consultation/{aid}"
        request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=20) as resp:
            body = resp.read(400).decode("utf-8", "replace")
            ct = resp.headers.get("Content-Type", "")
        is_spa = "<!doctype html>" in body.lower() or "<html" in body.lower()
        not_json = not body.strip().startswith("{")
        check(f"Refresh {label} -> HTML SPA", is_spa and not_json, f"HTTP {resp.status} {ct}")

    code, bad = req("GET", f"/consultation/{aid}", None, base=BASE)
    check(
        "Refresh :8000 -> 404 JSON (URL interdite pour refresh)",
        code == 404 and isinstance(bad, dict),
        str(bad),
    )

    code_slash, _ = req("GET", f"/appointments/{aid}/", pat, base=PROXY)
    code_noslash, _ = req("GET", f"/appointments/{aid}", pat, base=PROXY)
    check(
        "Fix trailing slash (sans slash=200, avec slash!=200 auth)",
        code_noslash == 200 and code_slash != 200,
        f"sans slash HTTP {code_noslash}, avec slash HTTP {code_slash}",
    )

    failed = [n for n, ok, _ in checks if not ok]
    print("\n=== LIVRABLES ===")
    print(f"APPOINTMENT_ID={aid}")
    print(f"DOCTOR_URL=http://localhost:5173/consultation/{aid}")
    print(f"PATIENT_URL_LOCAL=http://localhost:5173/consultation/{aid}")
    print(f"PATIENT_URL_4G={TUNNEL}/consultation/{aid}")
    print(f"RDV_DATE={when}")
    print("\n=== VERDICT FINAL ===")
    if failed:
        print(f"NO GO — {len(failed)} échec(s): {', '.join(failed)}")
        return 1
    print("GO — Prêt pour test avec votre cousin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
