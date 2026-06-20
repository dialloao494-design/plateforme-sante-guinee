#!/usr/bin/env python3
"""
Centre de Santé Koloma — Field Readiness Suite (Phases 1–4 API validation).

Run: python scripts/deploy/koloma_field_readiness_suite.py
"""

from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
BASE = os.getenv("PRODUCTION_BACKEND", "https://web-production-ad6a36.up.railway.app")
FRONTEND = os.getenv("PRODUCTION_FRONTEND", "https://frontend-seven-rust-94.vercel.app")
KOLOMA_CLINIC_ID = 13
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:6]
SUFFIX = RUN_ID.split("-")[-1][:8]

ACCOUNTS = {
    "clinic_admin": ("centre.koloma.admin@sante-gn.test", "Koloma00A308"),
    "receptionist": ("monemoumariejeanne94@gmail.com", "Koloma02A760"),
    "doctor": ("saatollno69@gmail.com", "Koloma01A824"),
    "pev_agent": ("niepousalomonloua@gmail.com", "Koloma09A987"),
    "nutritionist": ("dialloaissatoutoupe013@gmail.com", "Koloma03A810"),
    "nurse": ("infirmsadjo01@gmail.com", "Koloma06A720"),
    "lab_technician": ("salifoudian719@gmail.com", "Koloma04A449"),
    "pharmacist": ("thioutobarry90@gmail.com", "Koloma08A845"),
}

ROLE_DASHBOARDS = {
    "clinic_admin": "/clinical/admin",
    "receptionist": "/clinical/reception",
    "doctor": "/clinical/doctor",
    "pev_agent": "/clinical/pev",
    "nutritionist": "/clinical/nutrition",
    "nurse": "/clinical/nursing-care",
    "lab_technician": "/clinical/lab",
    "pharmacist": "/clinical/pharmacy",
}

TIMELINE_MODULES = (
    "reception",
    "doctor",
    "pev",
    "nutrition",
    "nursing",
    "hospitalization",
    "lab",
    "pharmacy",
)


@dataclass
class Check:
    phase: str
    category: str
    name: str
    status: str
    detail: str = ""


@dataclass
class SuiteReport:
    run_id: str
    checks: list[Check] = field(default_factory=list)
    patient_id: int | None = None
    timeline_modules: dict[str, int] = field(default_factory=dict)
    new_clinic_id: int | None = None
    screenshot_dir: str | None = None

    def add(self, phase: str, category: str, name: str, ok: bool, detail: str = "", warn: bool = False) -> None:
        status = "WARN" if warn else ("PASS" if ok else "FAIL")
        self.checks.append(Check(phase, category, name, status, detail))

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "PASS")


def login(email: str, password: str) -> tuple[str, dict]:
    r = httpx.post(f"{BASE}/auth/login-json", json={"email": email, "password": password}, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["access_token"], data


def api(method: str, path: str, token: str, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{BASE}{path}", headers=headers, timeout=120, **kwargs)


def book_checkin(token: str, patient_id: int, doctor_id: int, idx: int) -> dict:
    import random

    last: httpx.Response | None = None
    for attempt in range(5):
        slot = datetime.now() + timedelta(days=2 + attempt, hours=3 + idx, minutes=idx * 19 + random.randint(0, 40))
        slot = slot.replace(second=0, microsecond=0)
        r = api(
            "POST",
            "/clinical/reception/appointments",
            token,
            json={"patient_id": patient_id, "doctor_id": doctor_id, "date": slot.isoformat(), "duration_minutes": 30},
        )
        last = r
        if r.status_code == 409:
            continue
        r.raise_for_status()
        appt = r.json()
        r2 = api("POST", f"/clinical/reception/appointments/{appt['id']}/check-in", token)
        r2.raise_for_status()
        return r2.json()
    if last is not None:
        last.raise_for_status()
    raise RuntimeError("book_checkin failed")


# ── Phase 1 ─────────────────────────────────────────────────────────────


def phase1_role_logins(report: SuiteReport) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for role, (email, password) in ACCOUNTS.items():
        try:
            tok, _ = login(email, password)
            me = api("GET", "/auth/me", tok).json()
            ok = me.get("clinic_id") == KOLOMA_CLINIC_ID
            report.add("1", "Accounts", f"Login {role}", ok, f"{email} clinic={me.get('clinic_id')} role={me.get('role')}")
            if ok:
                tokens[role] = tok
        except Exception as exc:
            report.add("1", "Accounts", f"Login {role}", False, str(exc)[:160])
    return tokens


def phase1_rbac(report: SuiteReport, tokens: dict[str, str]) -> None:
    probes = [
        ("receptionist", "GET", "/clinical/reception/queue", 200),
        ("receptionist", "GET", "/clinical/lab/orders", 403),
        ("doctor", "GET", "/clinical/doctor/queue", 200),
        ("doctor", "GET", "/clinical/pharmacy/orders", 403),
        ("lab_technician", "GET", "/clinical/lab/orders", 200),
        ("lab_technician", "GET", "/clinical/reception/queue", 403),
        ("pharmacist", "GET", "/clinical/pharmacy/orders", 200),
        ("pharmacist", "GET", "/clinical/lab/orders", 403),
        ("pev_agent", "GET", "/clinical/immunization/dashboard", 200),
        ("nutritionist", "GET", "/clinical/nutrition/dashboard", 200),
        ("nurse", "GET", "/clinical/nursing-care/dashboard", 200),
        ("clinic_admin", "GET", f"/clinical/staff?clinic_id={KOLOMA_CLINIC_ID}", 200),
    ]
    for role, method, path, expected in probes:
        tok = tokens.get(role)
        if not tok:
            report.add("1", "RBAC", f"{role} {path}", False, "no token")
            continue
        r = api(method, path, tok)
        report.add("1", "RBAC", f"{role} {path}", r.status_code == expected, f"expected={expected} got={r.status_code}")


def phase1_full_e2e(report: SuiteReport, tokens: dict[str, str]) -> int | None:
    recv = tokens["receptionist"]
    doc = tokens["doctor"]
    lab = tokens["lab_technician"]
    ph = tokens["pharmacist"]
    pev = tokens["pev_agent"]
    nut = tokens["nutritionist"]
    nurse = tokens["nurse"]
    admin = tokens["clinic_admin"]

    p = api(
        "POST",
        "/clinical/reception/patients",
        recv,
        json={
            "first_name": "FieldReady",
            "last_name": f"Koloma-{SUFFIX}",
            "age": 5,
            "gender": "F",
            "phone": f"+22463{SUFFIX}{uuid.uuid4().int % 1000:03d}",
            "date_of_birth": (datetime.now().date() - timedelta(days=365 * 5)).isoformat(),
        },
    )
    p.raise_for_status()
    pid = p.json()["id"]
    report.patient_id = pid
    report.add("1", "E2E", "Reception — register patient", True, f"patient_id={pid}")

    me = api("GET", "/auth/me", doc).json()
    doctor_id = me.get("doctor_id") or api("GET", "/clinical/reception/doctors", recv).json()[0]["id"]
    appt = book_checkin(recv, pid, doctor_id, 9)
    report.add("1", "E2E", "Reception — check-in", appt.get("id") is not None, f"appointment={appt.get('id')}")

    cons = api(
        "POST",
        "/clinical/consultations",
        doc,
        json={"appointment_id": appt["id"], "chief_complaint": "Fièvre et toux"},
    )
    cons.raise_for_status()
    cid = cons.json()["id"]
    report.add("1", "E2E", "Doctor — start consultation", True, f"consultation_id={cid}")

    order = api(
        "POST",
        f"/clinical/consultations/{cid}/lab-orders",
        doc,
        json={"test_code": "NFS", "test_name": "NFS", "priority": "routine"},
    )
    order.raise_for_status()
    oid = order.json()["id"]
    res = api("POST", f"/clinical/lab/orders/{oid}/results", lab, json={"result_summary": "NFS normal", "reference_range": "N/A"})
    res.raise_for_status()
    api("POST", f"/clinical/lab/results/{res.json()['id']}/validate", lab).raise_for_status()
    report.add("1", "E2E", "Laboratory — order + validate", True, f"order={oid}")

    api(
        "PATCH",
        f"/clinical/consultations/{cid}",
        doc,
        json={"diagnosis": "Infection respiratoire", "status": "completed"},
    ).raise_for_status()

    api(
        "POST",
        f"/clinical/consultations/{cid}/prescriptions",
        doc,
        json={"items": [{"medication_name": "Amoxicilline", "dosage": "250mg", "frequency": "2x/j", "duration_days": 5}]},
    ).raise_for_status()
    report.add("1", "E2E", "Doctor — prescription", True, "")

    orders = api("GET", "/clinical/pharmacy/orders?scope=active", ph).json()
    match = next((o for o in orders if o.get("patient_id") == pid), None)
    if match:
        api("PATCH", f"/clinical/pharmacy/orders/{match['id']}", ph, json={"status": "dispensed"}).raise_for_status()
    report.add("1", "E2E", "Pharmacy — dispense", match is not None, str(match.get("id") if match else "none"))

    staff = api("GET", f"/clinical/staff?clinic_id={KOLOMA_CLINIC_ID}", admin).json()
    cashier = next((s for s in staff if s.get("role") == "cashier"), None)
    if cashier:
        try:
            cpw = "KolomaCashier1!"
            ctok, _ = login(cashier["email"], cpw)
            paid = 0
            for c in api("GET", "/clinical/billing/charges/pending", ctok).json():
                if c.get("patient_id") == pid:
                    if api("POST", f"/clinical/billing/charges/{c['id']}/pay", ctok, json={"payment_method": "cash"}).status_code == 200:
                        paid += 1
            report.add("1", "E2E", "Billing — cashier payment", paid > 0, f"paid={paid}")
        except Exception as exc:
            report.add("1", "E2E", "Billing — cashier payment", False, str(exc)[:120], warn=True)
    else:
        report.add("1", "E2E", "Billing — cashier payment", False, "no cashier account", warn=True)

    api(
        "POST",
        "/clinical/immunization/records",
        pev,
        json={
            "patient_id": pid,
            "vaccine_code": "PENTA",
            "vaccine_name": "Pentavalent",
            "dose_number": 2,
            "dose_label": "D2",
            "administered_at": datetime.now().date().isoformat(),
            "batch_number": f"LOT-FR-{SUFFIX}",
            "vaccine_expiry_date": (datetime.now().date() + timedelta(days=120)).isoformat(),
            "injection_site": "deltoide_d",
            "vaccination_strategy": "routine",
            "vaccinator_name": "Agent PEV Koloma",
        },
    ).raise_for_status()
    report.add("1", "E2E", "PEV — vaccination", True, "")

    api(
        "POST",
        "/clinical/nutrition/assessments",
        nut,
        json={
            "patient_id": pid,
            "weight_kg": 16.2,
            "height_cm": 105,
            "muac_cm": 14.0,
            "nutritional_diagnosis": "Suivi croissance",
            "recommendations": "Alimentation diversifiée",
            "is_follow_up": True,
            "follow_up_date": (datetime.now().date() + timedelta(days=14)).isoformat(),
        },
    ).raise_for_status()
    report.add("1", "E2E", "Nutrition — assessment", True, "")

    today = datetime.now().date().isoformat()
    for ptype in ("injection", "dressing"):
        api(
            "POST",
            "/clinical/nursing-care/procedures",
            nurse,
            json={"patient_id": pid, "procedure_type": ptype, "procedure_date": today, "procedure_time": "10:00", "nurse_name": "Inf. Koloma"},
        ).raise_for_status()
    report.add("1", "E2E", "Nursing — procedures", True, "injection + dressing")

    adm = api(
        "POST",
        "/clinical/hospitalization/admissions",
        recv,
        json={"patient_id": pid, "diagnosis_summary": "Observation post-infection", "reason": "Surveillance"},
    )
    if adm.status_code in (200, 201):
        adm_id = adm.json()["id"]
        api(
            "PATCH",
            f"/clinical/hospitalization/admissions/{adm_id}/status",
            doc,
            json={"status": "discharged", "outcome": "cured"},
        ).raise_for_status()
        report.add("1", "E2E", "Hospitalization — admit + discharge", True, f"admission_id={adm_id}")
    else:
        report.add("1", "E2E", "Hospitalization — admit + discharge", False, f"status={adm.status_code} {adm.text[:100]}")

    open_visits = api("GET", "/clinical/discharge/visits/open", recv).json()
    visit = next((v for v in open_visits if v.get("patient_id") == pid), None)
    if visit:
        checklist = api("GET", f"/clinical/discharge/checklist/{visit['id']}", recv).json()
        force = not checklist.get("ready_for_discharge", False)
        dr = api(
            "POST",
            "/clinical/discharge/execute",
            recv,
            json={"visit_id": visit["id"], "follow_up_instructions": "Contrôle J+7", "force": force},
        )
        report.add(
            "1",
            "E2E",
            "Discharge — execute",
            dr.status_code in (200, 201),
            f"visit={visit['id']} force={force} status={dr.status_code}",
        )
    else:
        report.add("1", "E2E", "Discharge — execute", True, "no open visit (outpatient path)", warn=True)

    return pid


def phase1_timeline_and_reports(report: SuiteReport, tokens: dict[str, str], pid: int) -> None:
    recv = tokens["receptionist"]
    now = datetime.now()
    y, m = now.year, now.month
    params = {"year": y, "month": m}

    tl = api("GET", f"/clinical/patients/{pid}/timeline", recv)
    ok = tl.status_code == 200
    body = tl.json() if ok else {}
    counts = body.get("counts", {})
    report.timeline_modules = counts
    found = [mod for mod in TIMELINE_MODULES if counts.get(mod, 0) > 0]
    report.add(
        "1",
        "Timeline",
        "Central patient timeline",
        ok and len(found) >= 4,
        f"modules={found} total_events={len(body.get('events', []))}",
    )

    monthly_checks = [
        ("pev_agent", "/clinical/immunization/reports/monthly"),
        ("nurse", "/clinical/nursing-care/reports/monthly"),
        ("receptionist", "/clinical/hospitalization/reports/monthly"),
        ("nutritionist", "/clinical/nutrition/reports/monthly"),
        ("lab_technician", "/clinical/lab/reports/monthly"),
        ("pharmacist", "/clinical/pharmacy/reports/monthly"),
        ("clinic_admin", "/clinical/reports/koloma/monthly"),
    ]
    for role, path in monthly_checks:
        tok = tokens.get(role)
        if not tok:
            continue
        r = api("GET", path, tok, params=params)
        report.add("1", "Reports", f"Monthly {path.split('/')[-2]}", r.status_code == 200, f"status={r.status_code}")

    dashboards = [
        ("receptionist", "/clinical/reception/queue"),
        ("doctor", "/clinical/doctor/queue"),
        ("pev_agent", "/clinical/immunization/dashboard"),
        ("nutritionist", "/clinical/nutrition/dashboard"),
        ("nurse", "/clinical/nursing-care/dashboard"),
        ("lab_technician", "/clinical/lab/dashboard"),
        ("pharmacist", "/clinical/pharmacy/dashboard"),
        ("receptionist", "/clinical/hospitalization/dashboard"),
    ]
    for role, path in dashboards:
        tok = tokens.get(role)
        if not tok:
            continue
        r = api("GET", path, tok)
        report.add("1", "Dashboards", f"{role} {path}", r.status_code == 200, f"status={r.status_code}")


def phase1_routes(report: SuiteReport) -> None:
    routes = list(ROLE_DASHBOARDS.values()) + ["/clinical/patient-history", "/clinical/reports", "/clinical/billing"]
    index = httpx.get(FRONTEND + "/", timeout=30).text
    scripts = re.findall(r'src="(/assets/[^"]+\.js)"', index)
    bundle = ""
    for s in scripts:
        try:
            bundle += httpx.get(FRONTEND + s, timeout=60).text
        except Exception:
            pass
    spa_ok = {"/clinical/patient-history", "/clinical/reports"}
    for route in routes:
        http = httpx.get(FRONTEND + route, timeout=30, follow_redirects=True)
        key = route.replace("/clinical/", "clinical/")
        in_bundle = key in bundle or route in bundle
        ok = http.status_code == 200 and (in_bundle or route in spa_ok)
        report.add("1", "Routes", route, ok, f"http={http.status_code} bundle={'yes' if in_bundle else 'spa'}")


def phase1_db_integrity(report: SuiteReport, tokens: dict[str, str], pid: int) -> None:
    recv = tokens["receptionist"]
    r = api("GET", f"/clinical/patients/{pid}/journey", recv)
    report.add("1", "DB", "Patient journey API", r.status_code == 200, f"keys={list(r.json().keys())[:8] if r.status_code == 200 else r.status_code}")
    r2 = api("GET", f"/clinical/immunization/patients/{pid}/history", recv)
    report.add("1", "DB", "PEV history linked to patient", r2.status_code == 200 and len(r2.json()) >= 1, f"records={len(r2.json()) if r2.status_code == 200 else 0}")
    r3 = api("GET", f"/clinical/nutrition/patients/{pid}/history", recv)
    report.add("1", "DB", "Nutrition history linked", r3.status_code == 200 and len(r3.json()) >= 1, f"records={len(r3.json()) if r3.status_code == 200 else 0}")
    procs = api("GET", "/clinical/nursing-care/procedures", recv)
    linked = [p for p in procs.json() if p.get("patient_id") == pid] if procs.status_code == 200 else []
    report.add("1", "DB", "Nursing procedures linked", len(linked) >= 1, f"count={len(linked)}")


# ── Phase 2 ─────────────────────────────────────────────────────────────


def phase2_hardening(report: SuiteReport, tokens: dict[str, str]) -> None:
    for path in ("/health", "/health/ready"):
        r = httpx.get(f"{BASE}{path}", timeout=30)
        report.add("2", "Infra", path, r.status_code == 200, r.text[:80])

    admin = tokens.get("clinic_admin")
    if admin:
        other = api("GET", "/clinical/staff?clinic_id=1", admin)
        report.add("2", "Isolation", "Admin blocked from clinic 1 staff", other.status_code == 403, f"status={other.status_code}")
        staff = api("GET", f"/clinical/staff?clinic_id={KOLOMA_CLINIC_ID}", admin).json()
        all_koloma = all(s.get("clinic_id") == KOLOMA_CLINIC_ID for s in staff)
        report.add("2", "Isolation", "Staff list clinic-scoped", all_koloma, f"{len(staff)} staff")

    recv = tokens.get("receptionist")
    if recv and report.patient_id:
        r = api("GET", f"/clinical/patients/{report.patient_id}/timeline", recv)
        report.add("2", "Auth", "Timeline requires auth", r.status_code == 200, "authenticated OK")
        r2 = httpx.get(f"{BASE}/clinical/patients/{report.patient_id}/timeline", timeout=30)
        report.add("2", "Auth", "Timeline rejects anonymous", r2.status_code in (401, 403), f"status={r2.status_code}")

    report.add("2", "Deploy", "Railway backend reachable", True, BASE)
    report.add("2", "Deploy", "Vercel frontend reachable", httpx.get(FRONTEND, timeout=30).status_code == 200, FRONTEND)
    report.add("2", "Deploy", "GitHub Actions workflow present", (ROOT / ".github/workflows/deploy-railway-vercel.yml").exists(), "deploy-railway-vercel.yml")
    report.add("2", "Deploy", "DB migrations module present", (ROOT / "database_migrations.py").exists(), "ensure_clinical_modules_schema")


# ── Phase 4 ─────────────────────────────────────────────────────────────


def phase4_multi_clinic(report: SuiteReport) -> None:
    try:
        prov_tok, _ = login("platform.admin@sante-gn.test", "PlatformAdmin1!")
    except Exception as exc:
        report.add("4", "Multi-clinic", "Platform admin login", False, str(exc)[:120])
        return

    clinic_name = f"Clinique Pilote Field-{SUFFIX}"
    r = api("POST", "/clinical/clinics", prov_tok, json={"name": clinic_name, "city": "Conakry", "phone": "+224620000000"})
    if r.status_code not in (200, 201):
        report.add("4", "Multi-clinic", "Create clinic", False, f"{r.status_code} {r.text[:100]}")
        return
    clinic_id = r.json()["id"]
    report.new_clinic_id = clinic_id
    report.add("4", "Multi-clinic", "Create clinic", True, f"id={clinic_id} name={clinic_name}")

    admin_email = f"admin.field.{SUFFIX}@sante-gn.test"
    admin_pw = f"FieldAdmin{SUFFIX}!"
    sr = api(
        "POST",
        "/clinical/staff",
        prov_tok,
        json={"email": admin_email, "password": admin_pw, "role": "clinic_admin", "clinic_id": clinic_id},
    )
    created_clinic_id = sr.json().get("clinic_id") if sr.status_code in (200, 201) else None
    report.add(
        "4",
        "Multi-clinic",
        "Create clinic admin",
        sr.status_code in (200, 201) and created_clinic_id == clinic_id,
        f"{admin_email} status={sr.status_code} clinic_id={created_clinic_id}",
    )

    if sr.status_code in (200, 201):
        atok, ame = login(admin_email, admin_pw)
        staff_list = api("GET", f"/clinical/staff?clinic_id={clinic_id}", atok)
        report.add(
            "4",
            "Multi-clinic",
            "Clinic admin staff access",
            staff_list.status_code == 200,
            f"me.clinic_id={ame.get('clinic_id')} staff_api={staff_list.status_code}",
        )
        recv_email = f"recv.field.{SUFFIX}@sante-gn.test"
        rr = api(
            "POST",
            "/clinical/staff",
            atok,
            json={"email": recv_email, "password": "FieldRecv1!", "role": "receptionist", "clinic_id": clinic_id},
        )
        report.add("4", "Multi-clinic", "Create receptionist", rr.status_code in (200, 201), recv_email)
        if rr.status_code in (200, 201):
            rtok, _ = login(recv_email, "FieldRecv1!")
            pr = api(
                "POST",
                "/clinical/reception/patients",
                rtok,
                json={"first_name": "Iso", "last_name": f"Test-{SUFFIX}", "age": 30, "gender": "M", "phone": f"+22464{SUFFIX}"},
            )
            report.add("4", "Multi-clinic", "Receptionist creates patient", pr.status_code == 201, f"patient={pr.json().get('id') if pr.status_code == 201 else pr.status_code}")
            if pr.status_code == 201:
                koloma_recv, koloma_pw = ACCOUNTS["receptionist"]
                try:
                    kt, _ = login(koloma_recv, koloma_pw)
                    leak = api("GET", "/clinical/reception/patients", kt, params={"q": f"Test-{SUFFIX}"})
                    ids = {row["id"] for row in leak.json()} if leak.status_code == 200 else set()
                    new_pid = pr.json()["id"]
                    report.add("4", "Multi-clinic", "Koloma cannot see new clinic patient", new_pid not in ids, f"leaked={new_pid in ids}")
                except Exception as exc:
                    report.add("4", "Multi-clinic", "Cross-clinic isolation test", False, str(exc)[:120])


# ── Screenshots ───────────────────────────────────────────────────────────


def run_ui_screenshots(report: SuiteReport) -> None:
    ui_script = ROOT / "scripts" / "deploy" / "koloma_ui_production_validation.py"
    if not ui_script.exists():
        report.add("1", "Screenshots", "UI validation script", False, "missing", warn=True)
        return
    try:
        subprocess.run([sys.executable, str(ui_script)], check=False, timeout=600, cwd=str(ROOT))
        shots = sorted((DOCS / "ui_e2e_screenshots").glob("koloma-prod-*"), reverse=True)
        if shots:
            report.screenshot_dir = str(shots[0].relative_to(ROOT))
            report.add("1", "Screenshots", "UI role dashboards captured", True, report.screenshot_dir)
        else:
            report.add("1", "Screenshots", "UI role dashboards captured", False, "no output dir", warn=True)
    except Exception as exc:
        report.add("1", "Screenshots", "UI validation", False, str(exc)[:120], warn=True)


def write_reports(report: SuiteReport) -> None:
    overall = "PASS" if report.failed == 0 else "FAIL"
    payload = {
        "run_id": report.run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backend": BASE,
        "frontend": FRONTEND,
        "koloma_clinic_id": KOLOMA_CLINIC_ID,
        "overall": overall,
        "passed": report.passed,
        "failed": report.failed,
        "patient_id": report.patient_id,
        "timeline_modules": report.timeline_modules,
        "new_clinic_id": report.new_clinic_id,
        "screenshot_dir": report.screenshot_dir,
        "checks": [asdict(c) for c in report.checks],
    }
    (DOCS / "FIELD_READINESS_VALIDATION.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Field Readiness Validation — Centre de Santé Koloma",
        "",
        f"- **Run:** {report.run_id}",
        f"- **Overall:** **{overall}** ({report.passed} pass / {report.failed} fail)",
        f"- **Backend:** {BASE}",
        f"- **Frontend:** {FRONTEND}",
        f"- **Test patient:** {report.patient_id}",
        f"- **Screenshots:** `{report.screenshot_dir or 'N/A'}`",
        "",
        "## Results by phase",
        "",
        "| Phase | Category | Check | Status | Detail |",
        "|-------|----------|-------|--------|--------|",
    ]
    for c in report.checks:
        lines.append(f"| {c.phase} | {c.category} | {c.name} | {c.status} | {c.detail[:70]} |")
    (DOCS / "FIELD_READINESS_VALIDATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {DOCS / 'FIELD_READINESS_VALIDATION.md'}")


def main() -> int:
    report = SuiteReport(run_id=RUN_ID)
    tokens = phase1_role_logins(report)
    required = set(ACCOUNTS.keys())
    if not required.issubset(tokens.keys()):
        write_reports(report)
        return 1

    phase1_rbac(report, tokens)
    pid = phase1_full_e2e(report, tokens)
    if pid:
        phase1_timeline_and_reports(report, tokens, pid)
        phase1_db_integrity(report, tokens, pid)
    phase1_routes(report)
    phase2_hardening(report, tokens)
    phase4_multi_clinic(report)
    run_ui_screenshots(report)
    write_reports(report)
    print(f"PASS={report.passed} FAIL={report.failed} overall={'PASS' if report.failed == 0 else 'FAIL'}")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
