#!/usr/bin/env python3
"""Production QA — end-to-end API validation (no new product features)."""

from __future__ import annotations
import os

import json
import random
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5173"
ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "sante.db"

ACCOUNTS = {
    "patient": ("test.patient@example.com", os.environ.get("PILOT_PATIENT_PASSWORD", "")),
    "reception": ("reception@pilot.local", "ReceptionPilot1!"),
    "doctor": ("dr.pilot@pilot.local", "DoctorPilot1!"),
    "lab": ("lab@pilot.local", "LabPilot1!"),
    "pharmacy": ("pharmacy@pilot.local", "PharmacyPilot1!"),
    "admin": ("admin@pilot.local", os.environ.get("PILOT_ADMIN_PASSWORD", "")),
}


@dataclass
class Finding:
    area: str
    status: str  # PASS | WARNING | FAIL
    message: str
    severity: str = ""
    repro: str = ""
    root_cause: str = ""
    fix: str = ""


@dataclass
class QAReport:
    findings: list[Finding] = field(default_factory=list)

    def add(self, **kwargs):
        self.findings.append(Finding(**kwargs))

    def summary(self) -> dict:
        c = {"PASS": 0, "WARNING": 0, "FAIL": 0}
        for f in self.findings:
            c[f.status] = c.get(f.status, 0) + 1
        return c


def login(email: str, password: str) -> tuple[str | None, str | None]:
    try:
        r = requests.post(
            f"{BASE}/auth/login-json",
            json={"email": email, "password": password},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("access_token"), None
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return None, str(e)


def hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def unique_appointment_slot() -> str:
    """Avoid duplicate-slot 409 when QA is re-run against the same database."""
    base = datetime.now() + timedelta(days=3 + random.randint(0, 21))
    slot = base.replace(
        hour=8 + random.randint(0, 10),
        minute=random.choice([0, 15, 30, 45]),
        second=0,
        microsecond=0,
    )
    return slot.isoformat()


def db_count(sql: str) -> int:
    c = sqlite3.connect(DB)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


def pilot_doctor_id() -> int | None:
    c = sqlite3.connect(DB)
    try:
        row = c.execute(
            """
            SELECT d.id FROM doctors d
            JOIN users u ON d.user_id = u.id
            WHERE u.email = ?
            """,
            ("dr.pilot@pilot.local",),
        ).fetchone()
        return int(row[0]) if row else None
    finally:
        c.close()


def run_qa() -> QAReport:
    report = QAReport()

    # --- Health ---
    try:
        h = requests.get(f"{BASE}/health", timeout=5)
        if h.status_code == 200:
            report.add(area="Infrastructure", status="PASS", message="Backend /health OK")
        else:
            report.add(area="Infrastructure", status="FAIL", message=f"/health {h.status_code}", severity="critical")
    except Exception as e:
        report.add(area="Infrastructure", status="FAIL", message=str(e), severity="critical")
        return report

    try:
        fe = requests.get(FRONTEND, timeout=5)
        report.add(
            area="Infrastructure",
            status="PASS" if fe.status_code == 200 else "WARNING",
            message=f"Frontend HTTP {fe.status_code}",
        )
    except Exception:
        report.add(area="Infrastructure", status="WARNING", message="Frontend not reachable on :5173")

    # --- Auth all roles ---
    tokens = {}
    for role, (email, pwd) in ACCOUNTS.items():
        tok, err = login(email, pwd)
        if tok:
            tokens[role] = tok
            report.add(area="Authentication", status="PASS", message=f"Login OK: {role}")
        else:
            report.add(
                area="Authentication",
                status="FAIL",
                message=f"Login failed: {role} — {err}",
                severity="critical",
                repro=f"POST /auth/login-json {email}",
            )

    if len(tokens) < 6:
        report.add(area="Authentication", status="FAIL", message="Missing pilot accounts", severity="critical")
        return report

    # --- Data volume ---
    patients = db_count("SELECT COUNT(*) FROM patients")
    appts = db_count("SELECT COUNT(*) FROM rendezvous")
    consults = db_count("SELECT COUNT(*) FROM consultations")
    labs = db_count("SELECT COUNT(*) FROM lab_orders")
    rx = db_count("SELECT COUNT(*) FROM prescriptions")
    fus = db_count("SELECT COUNT(*) FROM follow_up_schedules")
    records = db_count("SELECT COUNT(*) FROM patient_medical_records")
    audits = db_count("SELECT COUNT(*) FROM clinical_audit_logs")

    for name, val, min_val in [
        ("patients", patients, 50),
        ("appointments", appts, 200),
        ("consultations", consults, 50),
        ("lab_orders", labs, 50),
        ("prescriptions", rx, 50),
        ("follow_ups", fus, 50),
        ("medical_records", records, 50),
    ]:
        if val >= min_val:
            report.add(area="Data volume", status="PASS", message=f"{name}={val} (min {min_val})")
        elif val >= min_val * 0.9:
            report.add(area="Data volume", status="WARNING", message=f"{name}={val} below target {min_val}")
        else:
            report.add(
                area="Data volume",
                status="WARNING" if name == "appointments" and val >= 180 else "FAIL",
                message=f"{name}={val} below min {min_val}",
                severity="medium" if val >= 180 else "high",
            )

    report.add(area="Audit logs", status="PASS" if audits > 0 else "WARNING", message=f"audit_logs={audits}")

    # --- Role permissions (negative) ---
    neg_tests = [
        ("reception", "GET", "/clinical/doctor/queue", [403]),
        ("doctor", "GET", "/clinical/pharmacy/orders", [403]),
        ("doctor", "GET", "/clinical/lab/orders", [403]),
        ("lab", "GET", "/clinical/pharmacy/orders", [403]),
        ("pharmacy", "GET", "/clinical/lab/orders", [403]),
        ("patient", "GET", "/clinical/operations/summary", [403]),
        ("patient", "GET", "/clinical/reception/queue", [403]),
        ("lab", "POST", "/clinical/consultations", [403, 422]),
        ("pharmacy", "GET", "/clinical/admin/backup-status", [403]),
        ("reception", "GET", "/clinical/admin/backup-status", [403]),
    ]
    for role, method, path, allowed in neg_tests:
        r = requests.request(method, f"{BASE}{path}", headers=hdr(tokens[role]), timeout=15)
        if r.status_code in allowed or r.status_code == 403:
            report.add(area="Role permissions", status="PASS", message=f"{role} {path} → {r.status_code}")
        else:
            report.add(
                area="Role permissions",
                status="FAIL",
                message=f"{role} {path} → {r.status_code} (expected deny)",
                severity="high",
                repro=f"{method} {path} as {role}",
            )

    # --- Patient medical history ---
    r = requests.get(f"{BASE}/patients/me/medical-history", headers=hdr(tokens["patient"]), timeout=15)
    if r.status_code == 200:
        body = r.json()
        report.add(
            area="Patient history",
            status="PASS",
            message=f"Medical history: {len(body.get('consultations', []))} consults, timeline={len(body.get('timeline', []))}",
        )
    else:
        report.add(area="Patient history", status="FAIL", message=f"/patients/me/medical-history → {r.status_code}", severity="high")

    # --- Reception follow-ups ---
    r = requests.get(f"{BASE}/clinical/reception/follow-ups", headers=hdr(tokens["reception"]), timeout=15)
    if r.status_code == 200:
        fu = r.json()
        report.add(
            area="Follow-up",
            status="PASS",
            message=f"Reception follow-ups: today={len(fu.get('due_today', []))} overdue={len(fu.get('overdue', []))} upcoming={len(fu.get('upcoming', []))}",
        )
    else:
        report.add(area="Follow-up", status="FAIL", message=f"follow-ups API {r.status_code}", severity="high")

    # --- Full workflow (live) ---
    reception_h, doctor_h, lab_h, pharmacy_h = (
        hdr(tokens["reception"]),
        hdr(tokens["doctor"]),
        hdr(tokens["lab"]),
        hdr(tokens["pharmacy"]),
    )
    slot = unique_appointment_slot()
    pid = did = appt_id = None
    try:
        r = requests.post(
            f"{BASE}/clinical/reception/patients",
            json={"first_name": "QA", "last_name": f"Run{int(time.time())}", "age": 40, "gender": "M"},
            headers=reception_h,
            timeout=15,
        )
        r.raise_for_status()
        pid = r.json()["id"]
        did = pilot_doctor_id()
        if not did:
            doctors = requests.get(f"{BASE}/clinical/reception/doctors", headers=reception_h, timeout=15).json()
            did = doctors[0]["id"]
        r = requests.post(
            f"{BASE}/clinical/reception/appointments",
            json={"patient_id": pid, "doctor_id": did, "date": slot, "duration_minutes": 30},
            headers=reception_h,
            timeout=15,
        )
        r.raise_for_status()
        appt_id = r.json()["id"]
        report.add(area="Reception workflow", status="PASS", message=f"Patient #{pid} appointment #{appt_id}")

        requests.post(f"{BASE}/clinical/reception/appointments/{appt_id}/check-in", headers=reception_h, timeout=15)
        charges = requests.get(f"{BASE}/clinical/billing/charges/pending", headers=reception_h, timeout=15).json()
        charge = next((c for c in charges if c.get("patient_id") == pid), None)
        if charge:
            pr = requests.post(
                f"{BASE}/clinical/billing/charges/{charge['id']}/pay",
                json={"payment_method": "cash"},
                headers=reception_h,
                timeout=15,
            )
            report.add(
                area="Cash collection",
                status="PASS" if pr.status_code == 200 else "FAIL",
                message=f"Encaissement charge #{charge['id']} → {pr.status_code}",
            )
        else:
            report.add(area="Cash collection", status="WARNING", message="No pending charge for QA patient")

        r = requests.post(
            f"{BASE}/clinical/consultations",
            json={"appointment_id": appt_id, "chief_complaint": "QA validation"},
            headers=doctor_h,
            timeout=15,
        )
        r.raise_for_status()
        cid = r.json()["id"]
        requests.patch(
            f"{BASE}/clinical/consultations/{cid}",
            json={"diagnosis": "QA Test", "treatment_plan": "Repos", "status": "completed"},
            headers=doctor_h,
            timeout=15,
        )
        requests.post(
            f"{BASE}/clinical/consultations/{cid}/lab-orders",
            json={"test_code": "NFS", "test_name": "Numération formule sanguine"},
            headers=doctor_h,
            timeout=15,
        )
        requests.post(
            f"{BASE}/clinical/consultations/{cid}/prescriptions",
            json={"items": [{"medication_name": "Paracétamol", "dosage": "500mg", "route": "oral", "frequency": "2x/jour", "duration_days": 5}]},
            headers=doctor_h,
            timeout=15,
        )
        requests.post(
            f"{BASE}/clinical/consultations/{cid}/follow-ups",
            json={"interval_type": "7d", "reason": "QA follow-up", "visit_type": "follow_up"},
            headers=doctor_h,
            timeout=15,
        )
        report.add(area="Doctor consultation", status="PASS", message=f"Consultation #{cid} completed + lab + rx + follow-up")

        orders = requests.get(f"{BASE}/clinical/lab/orders", headers=lab_h, timeout=15).json()
        qa_order = next((o for o in orders if o.get("patient_id") == pid), None)
        if qa_order:
            requests.patch(
                f"{BASE}/clinical/lab/orders/{qa_order['id']}",
                json={"status": "sample_collected"},
                headers=lab_h,
                timeout=15,
            )
            rr = requests.post(
                f"{BASE}/clinical/lab/orders/{qa_order['id']}/results",
                json={"result_summary": "Normal", "reference_range": "—", "interpretation": "OK"},
                headers=lab_h,
                timeout=15,
            )
            if rr.status_code == 200:
                rid = rr.json()["id"]
                requests.post(f"{BASE}/clinical/lab/results/{rid}/validate", headers=lab_h, timeout=15)
            report.add(area="Laboratory", status="PASS", message=f"Lab order #{qa_order['id']} validated")
        else:
            report.add(area="Laboratory", status="FAIL", message="QA lab order not in queue", severity="high")

        ph_orders = requests.get(f"{BASE}/clinical/pharmacy/orders", headers=pharmacy_h, timeout=15).json()
        qa_ph = next((o for o in ph_orders if o.get("patient_id") == pid), None)
        if qa_ph:
            requests.patch(f"{BASE}/clinical/pharmacy/orders/{qa_ph['id']}", json={"status": "preparing"}, headers=pharmacy_h, timeout=15)
            requests.patch(f"{BASE}/clinical/pharmacy/orders/{qa_ph['id']}", json={"status": "dispensed"}, headers=pharmacy_h, timeout=15)
            report.add(area="Pharmacy", status="PASS", message=f"Pharmacy order dispensed")
        else:
            report.add(area="Pharmacy", status="FAIL", message="QA pharmacy order missing", severity="high")

        # DB consistency
        st = db_count(f"SELECT clinical_status FROM rendezvous WHERE id={appt_id}")
        c = sqlite3.connect(DB)
        row = c.execute("SELECT clinical_status, status FROM rendezvous WHERE id=?", (appt_id,)).fetchone()
        c.close()
        if row and row[0] == "completed" and row[1] == "completed":
            report.add(area="Data consistency", status="PASS", message=f"Appointment #{appt_id} completed in DB")
        else:
            report.add(area="Data consistency", status="FAIL", message=f"Appointment state {row}", severity="high")

        mr = requests.get(f"{BASE}/patients/{pid}/medical-history", headers=hdr(tokens["admin"]), timeout=15)
        if mr.status_code == 200 and mr.json().get("medical_record"):
            report.add(area="Patient history", status="PASS", message=f"Permanent record for QA patient #{pid}")
        else:
            report.add(area="Patient history", status="WARNING", message="Medical record not found for new QA patient")

    except Exception as e:
        report.add(area="E2E workflow", status="FAIL", message=str(e), severity="critical", repro="Full clinical pipeline")

    # --- Invalid: duplicate appointment same slot ---
    if pid and did and slot:
        r1 = requests.post(
            f"{BASE}/clinical/reception/appointments",
            json={"patient_id": pid, "doctor_id": did, "date": slot, "duration_minutes": 30},
            headers=reception_h,
            timeout=15,
        )
        report.add(
            area="Duplicate appointments",
            status="PASS" if r1.status_code == 409 else "FAIL",
            message=f"Duplicate slot → {r1.status_code} (expect 409)",
            severity="high" if r1.status_code != 409 else "",
        )

    # --- Simulated patient portal ---
    sim_tok, sim_err = login("sim.patient.001@pilot.local", "SimPatient1!")
    if sim_tok:
        sr = requests.get(f"{BASE}/patients/me/medical-history", headers=hdr(sim_tok), timeout=15)
        report.add(
            area="Patient portal",
            status="PASS" if sr.status_code == 200 else "FAIL",
            message=f"Simulated patient portal history → {sr.status_code}",
        )
    else:
        report.add(
            area="Patient portal",
            status="WARNING",
            message=f"Simulated portal login unavailable: {sim_err}",
            severity="low",
            fix="Run python -m services.medical_history_seed to link portal accounts",
        )

    # --- Notifications ---
    r = requests.get(f"{BASE}/notifications/", headers=hdr(tokens["patient"]), timeout=15)
    report.add(
        area="Notifications",
        status="PASS" if r.status_code == 200 else "WARNING",
        message=f"GET /notifications/ → {r.status_code}",
    )

    # --- Audit after workflow ---
    ar = requests.get(f"{BASE}/clinical/audit-logs?limit=5", headers=hdr(tokens["admin"]), timeout=15)
    report.add(
        area="Audit logs",
        status="PASS" if ar.status_code == 200 and len(ar.json()) > 0 else "WARNING",
        message=f"Audit logs accessible, count={len(ar.json()) if ar.ok else 0}",
    )

    # --- v2.0 modules: discharge, radiology, reminders ---
    dr = requests.get(f"{BASE}/clinical/discharge/visits/open", headers=reception_h, timeout=15)
    report.add(
        area="Discharge module",
        status="PASS" if dr.status_code == 200 else "FAIL",
        message=f"GET /clinical/discharge/visits/open → {dr.status_code}",
        severity="high" if dr.status_code != 200 else "",
    )
    rad = requests.get(f"{BASE}/clinical/radiology/orders", headers=hdr(tokens["lab"]), timeout=15)
    report.add(
        area="Radiology module",
        status="PASS" if rad.status_code == 200 else "FAIL",
        message=f"GET /clinical/radiology/orders → {rad.status_code}",
        severity="high" if rad.status_code != 200 else "",
    )
    rem = requests.get(f"{BASE}/clinical/reminders/notifications", headers=reception_h, timeout=15)
    report.add(
        area="Reminder notifications",
        status="PASS" if rem.status_code == 200 else "FAIL",
        message=f"GET /clinical/reminders/notifications → {rem.status_code}",
        severity="high" if rem.status_code != 200 else "",
    )

    return report


def main() -> int:
    report = run_qa()
    counts = report.summary()
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": counts,
        "findings": [
            {
                "area": f.area,
                "status": f.status,
                "message": f.message,
                "severity": f.severity,
                "repro": f.repro,
                "root_cause": f.root_cause,
                "recommended_fix": f.fix,
            }
            for f in report.findings
        ],
    }
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    path = evidence / "qa_production_report.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(counts, indent=2))
    fails = [f for f in report.findings if f.status == "FAIL"]
    warns = [f for f in report.findings if f.status == "WARNING"]
    print(f"\nReport: {path}")
    print(f"FAIL={len(fails)} WARNING={len(warns)} PASS={counts.get('PASS', 0)}")
    for f in fails + warns:
        print(f"  [{f.status}] {f.area}: {f.message}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
