#!/usr/bin/env python3
"""
Full production audit — routes, roles, auth, clinical workflow, security.
Run: python scripts/deploy/full_production_audit.py
Optional: --backend URL --frontend URL --smtp-test-email you@domain.com
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

DEFAULT_BACKEND = "https://web-production-ad6a36.up.railway.app"
DEFAULT_FRONTEND = "https://frontend-seven-rust-94.vercel.app"

KNOWN_ACCOUNTS = [
    ("clinic_admin", "clinic.admin.a@sante-gn.test", "ClinicAdminA1!"),
    ("reception_a", "reception.demo@sante-gn.test", "ReceptionDemo1!"),
    ("reception_b", "reception.beta@sante-gn.test", "ReceptionBeta1!"),
    ("doctor", "doctor.demo@sante-gn.test", "DoctorDemo1!"),
]

FRONTEND_ROUTES = [
    "/",
    "/login",
    "/signup",
    "/forgot-password",
    "/reset-password",
    "/verify-email",
    "/clinical/reception",
    "/clinical/nutrition",
    "/clinical/immunization",
    "/clinical/doctor",
    "/clinical/lab",
    "/clinical/pharmacy",
    "/clinical/midwife",
]

ROLE_API_CHECKS = [
    ("reception_a", "GET", "/clinical/reception/queue", [200]),
    ("reception_a", "GET", "/clinical/workflow/queue/reception", [200]),
    ("doctor", "GET", "/clinical/doctor/queue", [200]),
    ("doctor", "GET", "/clinical/workflow/queue/doctor", [200]),
    ("clinic_admin", "GET", "/clinical/operations/summary", [200]),
    ("clinic_admin", "GET", "/clinical/staff", [200]),
    ("reception_a", "GET", "/clinical/nutrition/patients/1/history", [200, 404]),
    ("reception_a", "GET", "/clinical/immunization/schedule", [200, 403]),
    ("reception_a", "GET", "/clinical/lab/orders", [403]),
    ("reception_a", "GET", "/clinical/pharmacy/orders", [403]),
]

RBAC_DENY = [
    ("reception_a", "GET", "/clinical/doctor/queue", [403], None),
    ("reception_a", "GET", "/clinical/admin/backup-status", [403], None),
    ("clinic_admin", "POST", "/clinical/clinics", [403], {"name": "RBAC Deny Clinic", "city": "Conakry"}),
]


@dataclass
class Finding:
    area: str
    status: str  # PASS | WARN | FAIL | BLOCKER
    message: str
    detail: str = ""


@dataclass
class AuditReport:
    backend: str
    frontend: str
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    findings: list[Finding] = field(default_factory=list)
    tokens: dict = field(default_factory=dict)
    journey: dict = field(default_factory=dict)

    def add(self, area: str, status: str, message: str, detail: str = "") -> None:
        self.findings.append(Finding(area, status, message, detail))

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.status] = out.get(f.status, 0) + 1
        return out


def login(base: str, email: str, password: str) -> tuple[str | None, str]:
    try:
        r = httpx.post(
            f"{base}/auth/login-json",
            json={"email": email, "password": password},
            timeout=45,
        )
        if r.status_code == 200:
            return r.json().get("access_token"), ""
        return None, f"{r.status_code} {r.text[:120]}"
    except Exception as exc:
        return None, str(exc)


def api(base: str, method: str, path: str, token: str | None = None, **kwargs) -> httpx.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{base}{path}", headers=headers, timeout=45, **kwargs)


def audit_infrastructure(report: AuditReport) -> None:
    b = report.backend
    for path in ("/health", "/health/ready", "/health/email", "/auth/email-status"):
        try:
            r = httpx.get(f"{b}{path}", timeout=30)
            ok = r.status_code == 200
            detail = r.text[:200]
            if path == "/health/email":
                body = r.json() if ok else {}
                if not body.get("configured"):
                    report.add("Email", "BLOCKER", "SMTP/Resend not configured on Railway", detail)
                else:
                    report.add("Email", "PASS", f"Email provider: {body.get('provider')}", detail)
            else:
                report.add("Infrastructure", "PASS" if ok else "FAIL", f"GET {path} -> {r.status_code}", detail)
        except Exception as exc:
            report.add("Infrastructure", "FAIL", f"GET {path} failed", str(exc))

    try:
        r = httpx.get(report.frontend, timeout=45, follow_redirects=True)
        report.add("Infrastructure", "PASS" if r.status_code == 200 else "FAIL", "Frontend home", str(r.status_code))
    except Exception as exc:
        report.add("Infrastructure", "FAIL", "Frontend unreachable", str(exc))

    for route in FRONTEND_ROUTES:
        try:
            r = httpx.get(report.frontend + route, timeout=45, follow_redirects=True)
            ok = r.status_code == 200
            report.add("Frontend routes", "PASS" if ok else "WARN", route, str(r.status_code))
        except Exception as exc:
            report.add("Frontend routes", "FAIL", route, str(exc))


def audit_auth(report: AuditReport) -> None:
    b = report.backend
    suffix = uuid.uuid4().hex[:10]
    doc_email = f"audit.doc.{suffix}@sante-gn.test"
    doc_pass = "AuditDoctor1!"

    r = httpx.post(
        f"{b}/auth/register",
        json={"email": doc_email, "password": doc_pass, "role": "doctor"},
        timeout=45,
    )
    if r.status_code == 201 and r.json().get("access_token"):
        report.add("Auth", "PASS", "Doctor register + token")
    else:
        report.add("Auth", "FAIL", "Doctor register", r.text[:150])

    tok, err = login(b, doc_email, doc_pass)
    report.add("Auth", "PASS" if tok else "FAIL", "Login after register", err)

    r = httpx.post(f"{b}/auth/register", json={"email": doc_email, "password": doc_pass, "role": "doctor"}, timeout=30)
    report.add("Auth", "PASS" if r.status_code in (409, 422) else "FAIL", "Duplicate email rejected", str(r.status_code))

    r = httpx.post(
        f"{b}/auth/register",
        json={"email": f"weak.{suffix}@test.com", "password": "short", "role": "patient"},
        timeout=30,
    )
    report.add("Auth", "PASS" if r.status_code == 422 else "FAIL", "Weak password rejected", str(r.status_code))

    r = httpx.post(f"{b}/auth/forgot-password", json={"email": doc_email}, timeout=30)
    report.add("Auth", "PASS" if r.status_code == 200 else "FAIL", "Forgot password endpoint", str(r.status_code))

    r = httpx.post(
        f"{b}/auth/reset-password",
        json={"token": "invalid", "new_password": "NewPass123!"},
        timeout=30,
    )
    report.add("Auth", "PASS" if r.status_code == 400 else "FAIL", "Invalid reset token rejected", str(r.status_code))

    if tok:
        r = api(b, "POST", "/auth/change-password", tok, json={"current_password": doc_pass, "new_password": "ChangedPass1!"})
        report.add("Auth", "PASS" if r.status_code == 200 else "FAIL", "Change password", r.text[:80])
        tok2, _ = login(b, doc_email, "ChangedPass1!")
        report.add("Auth", "PASS" if tok2 else "FAIL", "Login with new password")


def audit_roles(report: AuditReport) -> None:
    for role_key, email, password in KNOWN_ACCOUNTS:
        tok, err = login(report.backend, email, password)
        if tok:
            report.tokens[role_key] = tok
            report.add("Roles", "PASS", f"Login {role_key}", email)
        else:
            report.add("Roles", "FAIL", f"Login {role_key}", err)

    admin = report.tokens.get("clinic_admin")
    if admin:
        me = api(report.backend, "GET", "/auth/me", admin)
        if me.status_code == 200:
            report.journey["admin_clinic_id"] = me.json().get("clinic_id")

    admin = report.tokens.get("clinic_admin")
    recv = report.tokens.get("reception_a")
    if not admin or not recv:
        report.add("Clinical", "BLOCKER", "Cannot run clinical smoke — missing admin/reception login")
        return

    for role_key, method, path, expected in ROLE_API_CHECKS:
        tok = report.tokens.get(role_key)
        if not tok:
            report.add("Dashboards", "WARN", f"Skip {path} — no token for {role_key}")
            continue
        params = None
        if path == "/clinical/staff" and report.journey.get("admin_clinic_id"):
            params = {"clinic_id": report.journey["admin_clinic_id"]}
        r = api(report.backend, method, path, tok, params=params)
        ok = r.status_code in expected
        report.add("Dashboards", "PASS" if ok else "FAIL", f"{role_key} {method} {path}", str(r.status_code))

    for role_key, method, path, expected, body in RBAC_DENY:
        tok = report.tokens.get(role_key)
        if not tok:
            continue
        kwargs = {"json": body} if body else {}
        r = api(report.backend, method, path, tok, **kwargs)
        ok = r.status_code in expected
        report.add("Security RBAC", "PASS" if ok else "FAIL", f"{role_key} denied {path}", str(r.status_code))


def audit_isolation(report: AuditReport) -> None:
    ta = report.tokens.get("reception_a")
    tb = report.tokens.get("reception_b")
    if not ta or not tb:
        report.add("Isolation", "WARN", "Skip isolation — need reception_a and reception_b")
        return
    tag = uuid.uuid4().hex[:8]
    r = api(
        report.backend,
        "POST",
        "/clinical/reception/patients",
        ta,
        json={
            "first_name": "Iso",
            "last_name": tag,
            "age": 40,
            "gender": "F",
            "phone": f"+224622{tag[:6]}",
        },
    )
    if r.status_code != 201:
        report.add("Isolation", "FAIL", "Create patient clinic A", r.text[:100])
        return
    pid = r.json()["id"]
    r = api(report.backend, "GET", "/clinical/reception/patients", tb, params={"q": tag})
    ids = {row["id"] for row in r.json()} if r.status_code == 200 else set()
    report.add(
        "Isolation",
        "PASS" if pid not in ids else "FAIL",
        "Clinic B cannot see clinic A patient",
        f"patient_id={pid} visible_in_b={pid in ids}",
    )


def audit_full_journey(report: AuditReport) -> None:
    admin = report.tokens.get("clinic_admin")
    if not admin:
        return

    clinic_id = report.journey.get("admin_clinic_id")
    if not clinic_id:
        me = api(report.backend, "GET", "/auth/me", admin)
        clinic_id = me.json().get("clinic_id") if me.status_code == 200 else None
    if not clinic_id:
        report.add("Smoke journey", "FAIL", "Clinic admin has no clinic_id — cannot provision staff")
        return

    suffix = uuid.uuid4().hex[:8]
    journey: dict = {"suffix": suffix, "clinic_id": clinic_id}
    report.add("Smoke journey", "PASS", "Using existing clinic", f"id={clinic_id}")

    staff_specs = [
        ("receptionist", f"audit.recv.{suffix}@sante-gn.test", "AuditRecv1!"),
        ("nutritionist", f"audit.nutri.{suffix}@sante-gn.test", "AuditNutri1!"),
        ("midwife", f"audit.midwife.{suffix}@sante-gn.test", "AuditMidwife1!"),
        ("doctor", f"audit.doc.{suffix}@sante-gn.test", "AuditDoctor1!"),
        ("lab_technician", f"audit.lab.{suffix}@sante-gn.test", "AuditLab1!"),
        ("pharmacist", f"audit.pharma.{suffix}@sante-gn.test", "AuditPharma1!"),
    ]
    staff_tokens: dict[str, str] = {}
    for role, email, pwd in staff_specs:
        r = api(
            report.backend,
            "POST",
            "/clinical/staff",
            admin,
            json={"email": email, "password": pwd, "role": role, "clinic_id": clinic_id},
        )
        if r.status_code != 201:
            report.add("Smoke journey", "FAIL", f"Create staff {role}", r.text[:120])
            continue
        tok, err = login(report.backend, email, pwd)
        if tok:
            staff_tokens[role] = tok
            report.add("Smoke journey", "PASS", f"Staff {role} login", email)
        else:
            report.add("Smoke journey", "FAIL", f"Staff {role} login", err)

    recv = staff_tokens.get("receptionist")
    if not recv:
        return

    r = api(
        report.backend,
        "POST",
        "/clinical/reception/patients",
        recv,
        json={
            "first_name": "Journey",
            "last_name": suffix,
            "age": 7,
            "gender": "M",
            "phone": f"+224623{suffix}",
        },
    )
    if r.status_code != 201:
        report.add("Smoke journey", "FAIL", "Patient intake", r.text[:120])
        return
    patient_id = r.json()["id"]
    journey["patient_id"] = patient_id

    r = api(
        report.backend,
        "POST",
        "/clinical/workflow/visits",
        recv,
        json={"patient_id": patient_id, "workflow_type": "child"},
    )
    if r.status_code != 201:
        report.add("Smoke journey", "FAIL", "Start child visit", r.text[:120])
        return
    wf_id = r.json()["id"]
    journey["workflow_id"] = wf_id

    steps = [
        ("receptionist", "reception"),
        ("nutritionist", "nutrition"),
        ("midwife", "pev"),
        ("doctor", "doctor"),
    ]
    for role, dept in steps:
        tok = staff_tokens.get(role) or recv
        r = api(report.backend, "POST", f"/clinical/workflow/visits/{wf_id}/complete/{dept}", tok)
        if r.status_code != 200:
            report.add("Smoke journey", "FAIL", f"Complete {dept}", r.text[:120])
            return
        nxt = r.json().get("current_department")
        journey[f"after_{dept}"] = nxt

    nutri = staff_tokens.get("nutritionist")
    if nutri:
        r = api(
            report.backend,
            "POST",
            "/clinical/nutrition/assessments",
            nutri,
            json={
                "patient_id": patient_id,
                "weight_kg": 22.5,
                "height_cm": 115,
                "muac_cm": 14.2,
                "notes": f"Audit {suffix}",
            },
        )
        report.add(
            "Smoke journey",
            "PASS" if r.status_code == 201 else "WARN",
            "Nutrition assessment",
            str(r.status_code),
        )

    midwife = staff_tokens.get("midwife")
    if midwife:
        for path in ("/clinical/workflow/queue/pev", "/clinical/workflow/queue/midwife"):
            r = api(report.backend, "GET", path, midwife)
            report.add(
                "Smoke journey",
                "PASS" if r.status_code == 200 else "WARN",
                f"Midwife {path}",
                str(r.status_code),
            )
        r = api(report.backend, "GET", "/clinical/immunization/schedule", midwife)
        schedule = r.json() if r.status_code == 200 else []
        if schedule:
            item = schedule[0]
            r2 = api(
                report.backend,
                "POST",
                "/clinical/immunization/records",
                midwife,
                json={
                    "patient_id": patient_id,
                    "vaccine_code": item.get("vaccine_code") or item.get("code"),
                    "vaccine_name": item.get("vaccine_name") or item.get("name") or "BCG",
                    "dose_label": item.get("dose_label") or "D1",
                    "administered_at": datetime.utcnow().date().isoformat(),
                    "notes": "Audit PEV",
                },
            )
            report.add(
                "Smoke journey",
                "PASS" if r2.status_code == 201 else "WARN",
                "PEV record",
                r2.text[:100],
            )

    lab = staff_tokens.get("lab_technician")
    if lab:
        r = api(report.backend, "GET", "/clinical/lab/orders", lab)
        report.add(
            "Smoke journey",
            "PASS" if r.status_code == 200 else "WARN",
            "Laboratory queue",
            str(r.status_code),
        )

    pharma = staff_tokens.get("pharmacist")
    if pharma:
        r = api(report.backend, "GET", "/clinical/pharmacy/orders", pharma)
        report.add(
            "Smoke journey",
            "PASS" if r.status_code == 200 else "WARN",
            "Pharmacy queue",
            str(r.status_code),
        )

    report.journey = journey
    report.add("Smoke journey", "PASS", "Full child workflow completed", json.dumps(journey))


def write_markdown(report: AuditReport, path: Path) -> None:
    counts = report.counts()
    lines = [
        "# Production Audit Report",
        "",
        f"- **Backend:** {report.backend}",
        f"- **Frontend:** {report.frontend}",
        f"- **Started:** {report.started_at}",
        "",
        "## Summary",
        "",
        f"| Status | Count |",
        f"|--------|-------|",
    ]
    for status in ("PASS", "WARN", "FAIL", "BLOCKER"):
        if counts.get(status):
            lines.append(f"| {status} | {counts[status]} |")

    blockers = [f for f in report.findings if f.status == "BLOCKER"]
    fails = [f for f in report.findings if f.status == "FAIL"]
    if blockers:
        lines.extend(["", "## Blocking issues (clinic deployment)", ""])
        for f in blockers:
            lines.append(f"- **{f.area}:** {f.message} — {f.detail}")
    if fails:
        lines.extend(["", "## Failures", ""])
        for f in fails:
            lines.append(f"- **{f.area}:** {f.message} — {f.detail}")

    lines.extend(["", "## All findings", ""])
    for f in report.findings:
        lines.append(f"- [{f.status}] **{f.area}** — {f.message}" + (f" ({f.detail})" if f.detail else ""))

    if report.journey:
        lines.extend(["", "## Smoke journey artifact", "", "```json", json.dumps(report.journey, indent=2), "```"])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--frontend", default=DEFAULT_FRONTEND)
    parser.add_argument("--report", default="docs/PRODUCTION_AUDIT_REPORT.md")
    args = parser.parse_args()

    report = AuditReport(backend=args.backend.rstrip("/"), frontend=args.frontend.rstrip("/"))
    audit_infrastructure(report)
    audit_auth(report)
    audit_roles(report)
    audit_isolation(report)
    audit_full_journey(report)

    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_markdown(report, out)
    json_path = out.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "backend": report.backend,
                "frontend": report.frontend,
                "counts": report.counts(),
                "findings": [asdict(f) for f in report.findings],
                "journey": report.journey,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    counts = report.counts()
    print(f"Audit complete: PASS={counts.get('PASS',0)} WARN={counts.get('WARN',0)} FAIL={counts.get('FAIL',0)} BLOCKER={counts.get('BLOCKER',0)}")
    print(f"Report: {out}")
    if counts.get("BLOCKER") or counts.get("FAIL"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
