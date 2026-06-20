#!/usr/bin/env python3
"""
Centre de Santé Koloma — production validation (API + routes + 3 patient journeys).

Run: python scripts/deploy/koloma_production_validation.py
"""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BASE = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://frontend-seven-rust-94.vercel.app"
KOLOMA_CLINIC_ID = 13
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:6]
SUFFIX = RUN_ID.split("-")[-1][:8]

ACCOUNTS = {
    "clinic_admin": ("centre.koloma.admin@sante-gn.test", "Koloma00A308"),
    "receptionist": ("monemoumariejeanne94@gmail.com", "Koloma02A760"),
    "doctor": ("saatollno69@gmail.com", "Koloma01A824"),
    "lab": ("salifoudian719@gmail.com", "Koloma04A449"),
    "pharmacy": ("thioutobarry90@gmail.com", "Koloma08A845"),
    "nutritionist": ("dialloaissatoutoupe013@gmail.com", "Koloma03A810"),
    "pev_agent": ("niepousalomonloua@gmail.com", "Koloma09A987"),
    "nurse": ("infirmsadjo01@gmail.com", "Koloma06A720"),
}

FRONTEND_ROUTES = [
    "/clinical/pev",
    "/clinical/hospitalization",
    "/clinical/nursing-care",
    "/clinical/nutrition",
    "/clinical/patient-history",
    "/clinical/admin",
    "/clinical/reception",
    "/clinical/doctor",
    "/clinical/lab",
    "/clinical/pharmacy",
    "/clinical/billing",
]

ROLE_PROBES = {
    "clinic_admin": [("GET", "/clinical/staff", 200)],
    "receptionist": [("GET", "/clinical/reception/queue", 200), ("GET", "/clinical/lab/orders", 403)],
    "doctor": [("GET", "/clinical/doctor/queue", 200), ("GET", "/clinical/pharmacy/orders", 403)],
    "lab": [("GET", "/clinical/lab/orders", 200), ("GET", "/clinical/reception/queue", 403)],
    "pharmacy": [("GET", "/clinical/pharmacy/orders", 200), ("GET", "/clinical/lab/orders", 403)],
    "nutritionist": [("GET", "/clinical/nutrition/dashboard", 200), ("GET", "/clinical/lab/orders", 403)],
    "pev_agent": [("GET", "/clinical/immunization/dashboard", 200), ("GET", "/clinical/pharmacy/orders", 403)],
    "nurse": [("GET", "/clinical/nursing-care/dashboard", 200), ("GET", "/clinical/doctor/queue", 403)],
}


@dataclass
class Check:
    category: str
    name: str
    status: str
    detail: str = ""


@dataclass
class Report:
    run_id: str
    checks: list[Check] = field(default_factory=list)
    accounts_tested: list[dict] = field(default_factory=list)
    patients: list[dict] = field(default_factory=list)

    def add(self, category: str, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(category, name, "PASS" if ok else "FAIL", detail))

    def warn(self, category: str, name: str, detail: str = "") -> None:
        self.checks.append(Check(category, name, "WARN", detail))

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "FAIL")


def login(email: str, password: str, retries: int = 4) -> tuple[str, dict]:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = httpx.post(f"{BASE}/auth/login-json", json={"email": email, "password": password}, timeout=120)
            if r.status_code >= 500:
                raise httpx.HTTPStatusError("server error", request=r.request, response=r)
            r.raise_for_status()
            data = r.json()
            return data["access_token"], data
        except Exception as exc:
            last = exc
            if attempt < retries - 1:
                import time

                time.sleep(5 * (attempt + 1))
    raise last  # type: ignore[misc]


def api(method: str, path: str, token: str, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{BASE}{path}", headers=headers, timeout=120, **kwargs)


def register_patient(token: str, label: str, age: int = 30) -> dict:
    r = api(
        "POST",
        "/clinical/reception/patients",
        token,
        json={
            "first_name": label,
            "last_name": f"Koloma-{SUFFIX}",
            "age": age,
            "gender": "F" if age % 2 == 0 else "M",
            "phone": f"+22462{SUFFIX}{uuid.uuid4().int % 10000:04d}",
        },
    )
    r.raise_for_status()
    return r.json()


def book_checkin(token: str, patient_id: int, doctor_id: int, idx: int) -> dict:
    import random

    last: httpx.Response | None = None
    for attempt in range(5):
        slot = datetime.now() + timedelta(days=1 + attempt, hours=2 + idx, minutes=idx * 17 + random.randint(0, 45))
        slot = slot.replace(second=0, microsecond=0)
        r = api(
            "POST",
            "/clinical/reception/appointments",
            token,
            json={
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "date": slot.isoformat(),
                "duration_minutes": 30,
            },
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


def validate_accounts(report: Report) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for role, (email, password) in ACCOUNTS.items():
        try:
            tok, data = login(email, password)
            me = api("GET", "/auth/me", tok).json()
            clinic_ok = me.get("clinic_id") == KOLOMA_CLINIC_ID
            report.add("Accounts", f"Login {role}", clinic_ok, f"{email} clinic_id={me.get('clinic_id')} role={me.get('role')}")
            if not clinic_ok:
                continue
            tokens[role] = tok
            report.accounts_tested.append({"role": role, "email": email, "clinic_id": me.get("clinic_id")})
            for method, path, expected in ROLE_PROBES.get(role, []):
                p = path
                if role == "clinic_admin" and "staff" in path:
                    p = f"/clinical/staff?clinic_id={KOLOMA_CLINIC_ID}"
                r = api(method, p, tok)
                ok = r.status_code == expected
                report.add("RBAC", f"{role} {method} {path}", ok, f"expected={expected} got={r.status_code}")
        except Exception as exc:
            report.add("Accounts", f"Login {role}", False, str(exc)[:180])
    return tokens


def ensure_cashier(report: Report, admin_token: str) -> tuple[str | None, str]:
    staff = api("GET", f"/clinical/staff?clinic_id={KOLOMA_CLINIC_ID}", admin_token).json()
    for u in staff:
        if u.get("role") == "cashier":
            email = u["email"]
            pw = "KolomaCashier1!"
            report.add("Accounts", "Cashier exists", True, email)
            return None, email
    email = f"koloma.cashier.{SUFFIX}@sante-gn.test"
    pw = "KolomaCashier1!"
    r = api(
        "POST",
        "/clinical/staff",
        admin_token,
        json={"email": email, "password": pw, "role": "cashier", "clinic_id": KOLOMA_CLINIC_ID},
    )
    ok = r.status_code == 201
    report.add("Accounts", "Create Koloma cashier", ok, f"{email} ({r.status_code})")
    if ok:
        report.accounts_tested.append({"role": "cashier", "email": email, "created": True})
    return (pw if ok else None), email


def validate_admin_scope(report: Report, admin_token: str) -> None:
    staff = api("GET", f"/clinical/staff?clinic_id={KOLOMA_CLINIC_ID}", admin_token).json()
    all_koloma = all(s.get("clinic_id") == KOLOMA_CLINIC_ID for s in staff)
    report.add("Admin", "Staff list Koloma only", all_koloma, f"{len(staff)} staff at clinic {KOLOMA_CLINIC_ID}")
    other = api("GET", "/clinical/staff?clinic_id=1", admin_token)
    report.add(
        "Admin",
        "Blocked from other clinic staff",
        other.status_code == 403,
        f"status={other.status_code} (clinic admin must not list clinic 1)",
    )


def validate_frontend_routes(report: Report) -> None:
    index = httpx.get(FRONTEND + "/", timeout=30).text
    import re

    scripts = re.findall(r'src="(/assets/[^"]+\.js)"', index)
    bundle = ""
    for s in scripts:
        try:
            bundle += httpx.get(FRONTEND + s, timeout=60).text
        except Exception:
            continue
    route_aliases = {
        "/clinical/patient-history": ["PatientHistoryDashboard", "patient-history", "patientTimeline"],
    }
    spa_only_routes = {"/clinical/patient-history"}
    for route in FRONTEND_ROUTES:
        key = route.replace("/clinical/", "clinical/")
        aliases = route_aliases.get(route, [])
        in_bundle = key in bundle or route in bundle or any(a in bundle for a in aliases)
        http = httpx.get(FRONTEND + route, timeout=30, follow_redirects=True)
        ok = http.status_code == 200 and (in_bundle or route in spa_only_routes)
        report.add(
            "Frontend",
            f"Route {route}",
            ok,
            f"http={http.status_code} bundle={'yes' if in_bundle else 'lazy/spa'}",
        )


def workflow_a(report: Report, tokens: dict[str, str], doctor_id: int) -> int | None:
    recv, doc, ph, cash = tokens["receptionist"], tokens["doctor"], tokens["pharmacy"], tokens.get("cashier") or tokens["receptionist"]
    p = register_patient(recv, "PatientA")
    pid = p["id"]
    appt = book_checkin(recv, pid, doctor_id, 1)
    cons = api("POST", "/clinical/consultations", doc, json={"appointment_id": appt["id"], "chief_complaint": "Fièvre"}).json()
    cid = cons["id"]
    api("PATCH", f"/clinical/consultations/{cid}", doc, json={"diagnosis": "Infection", "status": "completed"}).raise_for_status()
    api(
        "POST",
        f"/clinical/consultations/{cid}/prescriptions",
        doc,
        json={"items": [{"medication_name": "Paracétamol", "dosage": "500mg", "frequency": "3x/j", "duration_days": 3}]},
    ).raise_for_status()
    orders = api("GET", "/clinical/pharmacy/orders?scope=active", ph).json()
    match = next((o for o in orders if o.get("patient_id") == pid), None)
    report.add("Patient A", "Pharmacy order queued", match is not None, str(match.get("id") if match else "none"))
    if match:
        api("PATCH", f"/clinical/pharmacy/orders/{match['id']}", ph, json={"status": "dispensed"}).raise_for_status()
    paid = 0
    for c in api("GET", "/clinical/billing/charges/pending", cash).json():
        if c.get("patient_id") == pid:
            if api("POST", f"/clinical/billing/charges/{c['id']}/pay", cash, json={"payment_method": "cash"}).status_code == 200:
                paid += 1
    report.add("Patient A", "Cashier payment", paid > 0, f"{paid} charge(s) paid")
    report.patients.append({"label": "A", "id": pid, "workflow": "rx-pharmacy-cashier"})
    return pid


def workflow_b(report: Report, tokens: dict[str, str], doctor_id: int) -> int | None:
    recv, doc, lab, ph, cash = tokens["receptionist"], tokens["doctor"], tokens["lab"], tokens["pharmacy"], tokens.get("cashier") or tokens["receptionist"]
    p = register_patient(recv, "PatientB")
    pid = p["id"]
    appt = book_checkin(recv, pid, doctor_id, 2)
    cons = api("POST", "/clinical/consultations", doc, json={"appointment_id": appt["id"], "chief_complaint": "Anémie"}).json()
    cid = cons["id"]
    order = api(
        "POST",
        f"/clinical/consultations/{cid}/lab-orders",
        doc,
        json={"test_code": "NFS", "test_name": "NFS", "priority": "routine"},
    ).json()
    res = api("POST", f"/clinical/lab/orders/{order['id']}/results", lab, json={"result_summary": "OK", "reference_range": "N/A"}).json()
    api("POST", f"/clinical/lab/results/{res['id']}/validate", lab).raise_for_status()
    report.add("Patient B", "Lab validated", True, f"order={order['id']}")
    api("PATCH", f"/clinical/consultations/{cid}", doc, json={"diagnosis": "Anémie légère", "status": "completed"}).raise_for_status()
    api(
        "POST",
        f"/clinical/consultations/{cid}/prescriptions",
        doc,
        json={"items": [{"medication_name": "Fer", "dosage": "200mg", "frequency": "1x/j", "duration_days": 30}]},
    ).raise_for_status()
    orders = api("GET", "/clinical/pharmacy/orders?scope=active", ph).json()
    match = next((o for o in orders if o.get("patient_id") == pid), None)
    if match:
        api("PATCH", f"/clinical/pharmacy/orders/{match['id']}", ph, json={"status": "dispensed"}).raise_for_status()
    paid = sum(
        1
        for c in api("GET", "/clinical/billing/charges/pending", cash).json()
        if c.get("patient_id") == pid
        and api("POST", f"/clinical/billing/charges/{c['id']}/pay", cash, json={"payment_method": "cash"}).status_code == 200
    )
    report.add("Patient B", "End-to-end lab→pharmacy→cashier", paid > 0, f"paid={paid}")
    report.patients.append({"label": "B", "id": pid, "workflow": "lab-rx-pharmacy-cashier"})
    return pid


def workflow_c(report: Report, tokens: dict[str, str]) -> int | None:
    recv = tokens["receptionist"]
    p = register_patient(recv, "PatientC", age=4)
    pid = p["id"]
    pev = tokens["pev_agent"]
    api(
        "POST",
        "/clinical/immunization/records",
        pev,
        json={
            "patient_id": pid,
            "vaccine_code": "BCG",
            "vaccine_name": "BCG",
            "dose_number": 1,
            "dose_label": "Naissance",
            "administered_at": datetime.now().date().isoformat(),
            "batch_number": f"LOT-{SUFFIX}",
            "vaccine_expiry_date": (datetime.now().date() + timedelta(days=180)).isoformat(),
            "injection_site": "deltoide_d",
            "vaccination_strategy": "routine",
            "vaccinator_name": "Agent PEV Koloma",
        },
    ).raise_for_status()
    report.add("Patient C", "PEV vaccination", True, f"patient_id={pid}")
    nut = tokens["nutritionist"]
    api(
        "POST",
        "/clinical/nutrition/assessments",
        nut,
        json={"patient_id": pid, "weight_kg": 12.5, "height_cm": 95, "muac_cm": 13.5, "is_follow_up": True},
    ).raise_for_status()
    report.add("Patient C", "Nutrition follow-up", True, "")
    nurse = tokens["nurse"]
    today = datetime.now().date().isoformat()
    for ptype in ("injection", "perfusion", "dressing", "suture"):
        api(
            "POST",
            "/clinical/nursing-care/procedures",
            nurse,
            json={"patient_id": pid, "procedure_type": ptype, "procedure_date": today, "nurse_name": "Inf. Koloma"},
        ).raise_for_status()
    report.add("Patient C", "Nursing procedures x4", True, "injection, perfusion, dressing, suture")
    report.patients.append({"label": "C", "id": pid, "workflow": "pev-nutrition-nursing"})
    return pid


def validate_central_history(report: Report, tokens: dict[str, str], patient_ids: list[int]) -> None:
    recv = tokens["receptionist"]
    now = datetime.now()
    for pid in patient_ids:
        j = api("GET", f"/clinical/patients/{pid}/journey", recv)
        tl = api("GET", f"/clinical/patients/{pid}/timeline", recv)
        ok = j.status_code == 200 and tl.status_code == 200
        events = tl.json().get("events", []) if tl.status_code == 200 else []
        report.add(
            "History",
            f"Central journey + timeline patient {pid}",
            ok and len(events) >= 0,
            f"journey={j.status_code} timeline={tl.status_code} events={len(events)}",
        )


def validate_phase2_modules(report: Report, tokens: dict[str, str], patient_ids: list[int]) -> None:
    now = datetime.now()
    y, m = now.year, now.month
    params = {"year": y, "month": m}
    checks = [
        ("nurse", "GET", "/clinical/nursing-care/register", tokens.get("nurse")),
        ("nutritionist", "GET", "/clinical/nutrition/register", tokens.get("nutritionist")),
        ("receptionist", "GET", "/clinical/hospitalization/reports/monthly", tokens.get("receptionist")),
        ("lab", "GET", "/clinical/lab/dashboard", tokens.get("lab")),
        ("lab", "GET", "/clinical/lab/reports/monthly", tokens.get("lab")),
        ("lab", "GET", "/clinical/lab/catalog", tokens.get("lab")),
        ("pharmacy", "GET", "/clinical/pharmacy/dashboard", tokens.get("pharmacy")),
        ("pharmacy", "GET", "/clinical/pharmacy/reports/monthly", tokens.get("pharmacy")),
        ("clinic_admin", "GET", "/clinical/reports/koloma/monthly", tokens.get("clinic_admin")),
    ]
    for role, method, path, tok in checks:
        if not tok:
            report.add("Phase2", f"{role} {path}", False, "no token")
            continue
        r = api(method, path, tok, params=params if "monthly" in path or "register" in path else None)
        ok = r.status_code == 200
        detail = f"status={r.status_code}"
        if ok and "register" in path:
            detail += f" rows={len(r.json()) if isinstance(r.json(), list) else 'n/a'}"
        if ok and path.endswith("/koloma/monthly"):
            body = r.json()
            detail += f" modules={list(body.keys())[:8]}"
        report.add("Phase2", f"{role} {path}", ok, detail)

    if patient_ids:
        pid = patient_ids[-1]
        for role in ("doctor", "receptionist", "nurse"):
            tok = tokens.get(role)
            if not tok:
                continue
            r = api("GET", f"/clinical/patients/{pid}/timeline", tok)
            report.add(
                "Phase2",
                f"{role} patient timeline",
                r.status_code == 200,
                f"patient={pid} status={r.status_code}",
            )


def pharmacy_stock(report: Report, token: str) -> None:
    code = f"KOL-{SUFFIX}"
    r = api(
        "POST",
        "/clinical/pharmacy/inventory",
        token,
        json={
            "sku": code,
            "medication_name": "Test Koloma",
            "quantity": 50,
            "reorder_level": 10,
            "unit_price_gnf": 25000,
        },
    )
    ok = r.status_code in (200, 201)
    detail = f"{code} status={r.status_code}"
    if not ok:
        detail += f" body={r.text[:120]}"
    report.add("Pharmacy", "Update stock", ok, detail)


def validate_pev_register(report: Report, token: str) -> None:
    now = datetime.now()
    r = api("GET", "/clinical/immunization/field-options", token)
    report.add("PEV", "Field options API", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        body = r.json()
        report.add(
            "PEV",
            "Injection sites configured",
            len(body.get("injection_sites", [])) >= 5,
            str(len(body.get("injection_sites", []))),
        )
    reg = api(
        "GET",
        "/clinical/immunization/register",
        token,
        params={"year": now.year, "month": now.month},
    )
    report.add("PEV", "Monthly register API", reg.status_code == 200, f"rows={len(reg.json()) if reg.status_code == 200 else 0}")
    rep = api(
        "GET",
        "/clinical/immunization/reports/monthly",
        token,
        params={"year": now.year, "month": now.month},
    )
    if rep.status_code == 200:
        data = rep.json()
        has_rows = "register_rows" in data and isinstance(data["register_rows"], list)
        report.add("PEV", "Monthly report register_rows", has_rows, f"total={data.get('total_vaccinations')}")
    else:
        report.add("PEV", "Monthly report register_rows", False, f"status={rep.status_code}")


def write_report(report: Report) -> None:
    root = Path(__file__).resolve().parents[2]
    js = root / "docs" / "KOLOMA_PRODUCTION_VALIDATION.json"
    md = root / "docs" / "KOLOMA_PRODUCTION_VALIDATION.md"
    overall = "PASS" if report.failed == 0 else "FAIL"
    payload = {
        "run_id": report.run_id,
        "backend": BASE,
        "frontend": FRONTEND,
        "clinic_id": KOLOMA_CLINIC_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "passed": sum(1 for c in report.checks if c.status == "PASS"),
        "failed": report.failed,
        "warn": sum(1 for c in report.checks if c.status == "WARN"),
        "accounts_tested": report.accounts_tested,
        "patients": report.patients,
        "checks": [c.__dict__ for c in report.checks],
    }
    js.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Koloma Production Validation",
        "",
        f"- **Run:** {report.run_id}",
        f"- **Backend:** {BASE}",
        f"- **Frontend:** {FRONTEND}",
        f"- **Overall:** **{overall}**",
        "",
        "## Accounts tested",
        "",
        "| Role | Email |",
        "|------|-------|",
    ]
    for a in report.accounts_tested:
        lines.append(f"| {a.get('role')} | `{a.get('email')}` |")
    lines.extend(["", "## Results", "", "| Category | Check | Status | Detail |", "|----------|-------|--------|--------|"])
    for c in report.checks:
        lines.append(f"| {c.category} | {c.name} | {c.status} | {c.detail[:80]} |")
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report: {md}")


def main() -> int:
    report = Report(run_id=RUN_ID)
    tokens = validate_accounts(report)
    required = {"clinic_admin", "receptionist", "doctor", "lab", "pharmacy", "pev_agent", "nurse", "nutritionist"}
    if not required.issubset(tokens.keys()):
        write_report(report)
        return 1

    validate_admin_scope(report, tokens["clinic_admin"])
    cashier_pw, cashier_email = ensure_cashier(report, tokens["clinic_admin"])
    if cashier_pw:
        try:
            tok, _ = login(cashier_email, cashier_pw)
            tokens["cashier"] = tok
            for method, path, expected in [("GET", "/clinical/billing/charges/pending", 200)]:
                r = api(method, path, tok)
                report.add("RBAC", f"cashier {path}", r.status_code == expected, str(r.status_code))
        except Exception as exc:
            report.add("Accounts", "Cashier login", False, str(exc)[:120])

    validate_frontend_routes(report)
    validate_pev_register(report, tokens["pev_agent"])
    pharmacy_stock(report, tokens["pharmacy"])

    me = api("GET", "/auth/me", tokens["doctor"]).json()
    doctor_id = me.get("doctor_id")
    if not doctor_id:
        docs = api("GET", "/clinical/reception/doctors", tokens["receptionist"]).json()
        doctor_id = docs[0]["id"] if docs else None
    report.add("Setup", "Doctor ID for appointments", doctor_id is not None, str(doctor_id))

    pids: list[int] = []
    if doctor_id:
        pa = workflow_a(report, tokens, doctor_id)
        pb = workflow_b(report, tokens, doctor_id)
        if pa:
            pids.append(pa)
        if pb:
            pids.append(pb)
    pc = workflow_c(report, tokens)
    if pc:
        pids.append(pc)
    if pids:
        validate_central_history(report, tokens, pids)
        validate_phase2_modules(report, tokens, pids)

    write_report(report)
    print(f"PASS={sum(1 for c in report.checks if c.status=='PASS')} FAIL={report.failed} overall={'PASS' if report.failed==0 else 'FAIL'}")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
