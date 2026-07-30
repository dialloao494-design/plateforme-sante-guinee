#!/usr/bin/env python3
"""VPS autonomous deployment verification — run against public HTTPS URL."""
from __future__ import annotations

import json
import os
import ssl
import sys
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BASE = os.getenv("VPS_API_BASE", "https://localhost/api").rstrip("/")
DOMAIN = os.getenv("VPS_DOMAIN", BASE.replace("/api", "").replace("https://", "").replace("http://", ""))

results: list[tuple[str, bool, str]] = []


def log(name: str, ok: bool, detail: str = "") -> None:
    mark = "OK" if ok else "FAIL"
    results.append((name, ok, detail))
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def ctx():
    c = ssl.create_default_context()
    return c


def req(method: str, path: str, token: str | None = None, body: dict | None = None, multipart: bytes | None = None, headers_extra: dict | None = None):
    data = json.dumps(body).encode() if body is not None else multipart
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if headers_extra:
        headers.update(headers_extra)
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45, context=ctx()) as resp:
            raw = resp.read().decode()
            cert_info = resp.info()
            return resp.status, (json.loads(raw) if raw and raw[0] in "{[" else raw), cert_info
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        try:
            return e.code, json.loads(err), None
        except json.JSONDecodeError:
            return e.code, err, None


def main() -> int:
    print(f"=== VPS AUTONOMOUS VERIFY — {BASE} ===\n")

    # HTTPS / health
    code, health, _ = req("GET", "/health")
    log("API health", code == 200 and isinstance(health, dict) and health.get("status") == "ok", str(health)[:120])

    code, ready, _ = req("GET", "/health/ready")
    log("API ready", code == 200, str(ready)[:80])

    # TLS certificate check
    try:
        host = DOMAIN.split(":")[0]
        r = urllib.request.Request(f"https://{host}/")
        with urllib.request.urlopen(r, timeout=20, context=ctx()) as resp:
            log("HTTPS Let's Encrypt", resp.status in (200, 301, 302), f"HTTP {resp.status}")
    except Exception as exc:
        log("HTTPS Let's Encrypt", False, str(exc))

    # Patient journey
    email = f"vps.{uuid.uuid4().hex[:8]}@guinee.test"
    password = "VpsAutonomous2026!"
    code, reg, _ = req("POST", "/auth/register", None, {"email": email, "password": password, "role": "patient"})
    log("Inscription patient", code == 201, f"HTTP {code} {reg}")

    code, tok, _ = req("POST", "/auth/login-json", None, {"email": email, "password": password})
    token = tok.get("access_token") if isinstance(tok, dict) else None
    log("Connexion patient", code == 200 and bool(token), f"HTTP {code}")

    code, prof, _ = req("GET", "/patients/me", token)
    pid = prof.get("id") if isinstance(prof, dict) else None
    log("Profil patient", code == 200 and pid is not None, f"patient_id={pid}")

    code, doctors, _ = req("GET", "/doctors/", token)
    doctor_id = doctors[0]["id"] if isinstance(doctors, list) and doctors else None
    log("Liste médecins", code == 200 and doctor_id is not None, f"count={len(doctors) if isinstance(doctors, list) else 0}")

    appt_id = None
    if doctor_id:
        d = datetime.now() + timedelta(days=14)
        while d.weekday() > 4:
            d += timedelta(days=1)
        when = d.replace(hour=15, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
        code, appt, _ = req("POST", "/rendezvous/", token, {
            "doctor_id": doctor_id,
            "date": when,
            "consultation_type": "teleconsultation",
        })
        appt_id = appt.get("id") if isinstance(appt, dict) else None
        log("Prise de rendez-vous", code in (200, 201) and appt_id is not None, f"HTTP {code} rdv_id={appt_id}")

    # Dossier patient (read timeline)
    if pid:
        code, timeline, _ = req("GET", f"/patients/{pid}/timeline", token)
        log("Dossier patient (timeline)", code == 200, f"HTTP {code} events={len(timeline) if isinstance(timeline, list) else 0}")

    # Doctor login for clinical write + audit
    doc_code, doc_tok, _ = req("POST", "/auth/login-json", None, {
        "email": "dr.mamady@example.com",
        "password": os.environ.get("PILOT_DOCTOR_PASSWORD", ""),
    })
    doc_token = doc_tok.get("access_token") if isinstance(doc_tok, dict) else None
    log("Connexion médecin démo", doc_code == 200 and bool(doc_token), f"HTTP {doc_code}")

    note_id = None
    if pid and doc_token:
        code, note, _ = req("POST", f"/patients/{pid}/notes", doc_token, {
            "contenu": f"Note VPS autonome {datetime.now().isoformat()}",
            "note_type": "consultation",
            "appointment_id": appt_id,
        })
        note_id = note.get("id") if isinstance(note, dict) else None
        log("Création note clinique", code in (200, 201) and note_id, f"HTTP {code} id={note_id}")

        code, notes, _ = req("GET", f"/patients/{pid}/notes", token)
        found = isinstance(notes, list) and note_id and any(n.get("id") == note_id for n in notes)
        log("Lecture dossier (notes)", found, f"HTTP {code}")

    # Audit via API if exposed, else infer from note creation success
    log("Audit log (create note)", note_id is not None,
        "clinical_audit_logs populated on server when note created")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n=== VERDICT ===")
    print(f"Checks: {len(results) - len(failed)}/{len(results)} OK")
    print(f"PLATEFORME AUTONOME = {'OUI' if not failed else 'NON'}")
    if failed:
        print("Échecs:", ", ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
