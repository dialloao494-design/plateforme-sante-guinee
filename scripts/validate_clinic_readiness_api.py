#!/usr/bin/env python3
"""API evidence for clinic readiness features — run while backend is on :8000."""

from __future__ import annotations

import json
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence"


def login(email: str, password: str) -> str:
    r = requests.post(f"{BASE}/auth/login-json", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    EVIDENCE_DIR.mkdir(exist_ok=True)
    evidence: dict = {}

    accounts = {
        "admin": ("admin@pilot.local", "AdminPilot1!"),
        "reception": ("reception@pilot.local", "ReceptionPilot1!"),
        "doctor": ("dr.pilot@pilot.local", "DoctorPilot1!"),
    }
    tokens = {}
    for role, (email, pwd) in accounts.items():
        tokens[role] = login(email, pwd)
        time.sleep(0.3)

    admin_h, reception_h, doctor_h = hdr(tokens["admin"]), hdr(tokens["reception"]), hdr(tokens["doctor"])

    # 1 Audit
    r = requests.get(f"{BASE}/clinical/audit-logs?limit=10", headers=reception_h, timeout=30)
    evidence["1_audit_logs"] = {"status": r.status_code, "count": len(r.json()) if r.ok else r.text, "sample": r.json()[:3] if r.ok else None}

    # 2 Timeline + workflow seed
    slot = (datetime.now() + timedelta(days=2, hours=random.randint(1, 8))).replace(second=0, microsecond=0).isoformat()
    r = requests.post(
        f"{BASE}/clinical/reception/patients",
        json={"first_name": "Evidence", "last_name": "Clinic", "age": 34, "gender": "F", "phone": "+224620111222"},
        headers=reception_h,
        timeout=30,
    )
    r.raise_for_status()
    patient_id = r.json()["id"]
    doctors = requests.get(f"{BASE}/clinical/reception/doctors", headers=reception_h, timeout=30).json()
    doctor_id = doctors[0]["id"]
    r = requests.post(
        f"{BASE}/clinical/reception/appointments",
        json={"patient_id": patient_id, "doctor_id": doctor_id, "date": slot, "duration_minutes": 30},
        headers=reception_h,
        timeout=30,
    )
    r.raise_for_status()
    appt_id = r.json()["id"]
    requests.post(f"{BASE}/clinical/reception/appointments/{appt_id}/check-in", headers=reception_h, timeout=30)
    r = requests.post(
        f"{BASE}/clinical/consultations",
        json={"appointment_id": appt_id, "chief_complaint": "Evidence run"},
        headers=doctor_h,
        timeout=30,
    )
    r.raise_for_status()
    consultation_id = r.json()["id"]
    requests.post(
        f"{BASE}/clinical/consultations/{consultation_id}/lab-orders",
        json={"test_code": "GLU", "test_name": "Glycémie"},
        headers=doctor_h,
        timeout=30,
    )
    requests.post(
        f"{BASE}/clinical/consultations/{consultation_id}/prescriptions",
        json={"items": [{"medication_name": "Paracétamol", "dosage": "500mg", "frequency": "2x/jour", "duration_days": 5}]},
        headers=doctor_h,
        timeout=30,
    )

    r = requests.get(f"{BASE}/patients/{patient_id}/timeline", headers=doctor_h, timeout=30)
    types = sorted({e["event_type"] for e in r.json()}) if r.ok else []
    evidence["2_timeline"] = {"status": r.status_code, "patient_id": patient_id, "event_types": types}

    # 3 Documents
    r = requests.get(f"{BASE}/patients/{patient_id}/documents", headers=doctor_h, timeout=30)
    evidence["3_documents"] = {"status": r.status_code, "count": len(r.json()) if r.ok else r.text}

    # 4 Backup
    r = requests.get(f"{BASE}/clinical/admin/backup-status", headers=admin_h, timeout=30)
    evidence["4_backup"] = r.json() if r.ok else {"status": r.status_code}

    # 5-8 Billing
    pending = requests.get(f"{BASE}/clinical/billing/charges/pending", headers=reception_h, timeout=30)
    charges = pending.json() if pending.ok else []
    by_type = {}
    for c in charges:
        by_type.setdefault(c["charge_type"], []).append(c)
    evidence["5_consultation_billing"] = {"pending_consultation": len(by_type.get("consultation", []))}
    evidence["6_laboratory_billing"] = {"pending_laboratory": len(by_type.get("laboratory", []))}
    evidence["7_pharmacy_billing"] = {"pending_pharmacy": len(by_type.get("pharmacy", []))}

    paid = []
    for c in charges:
        pr = requests.post(
            f"{BASE}/clinical/billing/charges/{c['id']}/pay",
            json={"payment_method": "cash"},
            headers=reception_h,
            timeout=30,
        )
        paid.append({"id": c["id"], "type": c["charge_type"], "status": pr.status_code, "amount_gnf": c["amount_gnf"]})
        time.sleep(0.2)
    evidence["payments"] = paid

    r = requests.get(f"{BASE}/clinical/billing/revenue/daily", headers=reception_h, timeout=30)
    evidence["8_daily_revenue"] = r.json() if r.ok else {"status": r.status_code}

    out = EVIDENCE_DIR / "api_evidence.json"
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(f"\nWrote {out}")
    ok = (
        evidence["1_audit_logs"]["status"] == 200
        and "cis_consultation" in evidence["2_timeline"].get("event_types", [])
        and evidence["8_daily_revenue"].get("total_collected_gnf", 0) > 0
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
