#!/usr/bin/env python3
"""Quick audit of pilot clinic account assignment (API must be running on :8000)."""
from __future__ import annotations
import os

import json
import sys

import requests

BASE = "http://127.0.0.1:8000"

ACCOUNTS = [
    ("admin@pilot.local", os.environ.get("PILOT_ADMIN_PASSWORD", ""), "admin"),
    ("reception@pilot.local", "ReceptionPilot1!", "receptionist"),
    ("cashier@pilot.local", "CashierPilot1!", "cashier"),
    ("dr.pilot@pilot.local", "DoctorPilot1!", "doctor"),
    ("lab@pilot.local", "LabPilot1!", "lab_technician"),
    ("pharmacy@pilot.local", "PharmacyPilot1!", "pharmacist"),
    ("dr.mamady@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", ""), "doctor"),
    ("test.patient@example.com", os.environ.get("PILOT_PATIENT_PASSWORD", ""), "patient"),
]


def login(email: str, password: str) -> tuple[int, dict]:
    r = requests.post(f"{BASE}/auth/login-json", json={"email": email, "password": password}, timeout=15)
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    return r.status_code, body


def probe(token: str, path: str) -> tuple[int, str]:
    r = requests.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    text = r.text[:120] if not r.ok else "ok"
    return r.status_code, text


def main() -> int:
    rows = []
    for email, pwd, expected_role in ACCOUNTS:
        code, body = login(email, pwd)
        row = {"email": email, "expected_role": expected_role, "login": code}
        if code == 200 and body.get("access_token"):
            tok = body["access_token"]
            role = body.get("role")
            row["role"] = role
            for path in (
                "/clinical/reception/queue",
                "/clinical/doctor/queue",
                "/clinical/lab/orders",
                "/clinical/pharmacy/orders",
                "/clinical/admin/backup-status",
            ):
                sc, detail = probe(tok, path)
                row[path] = {"status": sc, "detail": detail}
        else:
            row["error"] = body
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    out_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "evidence" / "audit_accounts.json"
    out_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
