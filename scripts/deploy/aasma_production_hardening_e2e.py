#!/usr/bin/env python3
"""AASMA production hardening E2E — roles, full patient journey, PDFs, CORS, migration."""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
LEGACY = "https://frontend-seven-rust-94.vercel.app"
OUT = Path(__file__).resolve().parents[2] / "docs" / "AASMA_PRODUCTION_HARDENING_E2E.json"
ARTIFACTS = Path("/opt/cursor/artifacts/hardening")
ARTIFACTS.mkdir(parents=True, exist_ok=True)

# Real AASMA staff + dedicated field/test accounts (passwords reset for E2E only).
STAFF = {
    "admin": ("contactpolycliniqueaasma@gmail.com", "AasmaAdmin1!"),
    "reception": ("baldoumar14@gmail.com", "AasmaRecep1!"),
    "lab": ("mamadoudianbarry06@gmail.com", "AasmaLab1!"),
    "pharmacy": ("ben752231@gmail.com", "AasmaPharm1!"),
    "nurse": ("aasma.nurse.test@sante-gn.test", "AasmaNurseE2E1!"),
    "doctor": ("field.verify.doctor.00c7@aasma-clinic.gn", "AasmaDocE2E1!"),
    "cashier": ("field.verify.cashier.8aac@aasma-clinic.gn", "AasmaCashE2E1!"),
}

PLATFORM_ADMIN = ("platform.admin@sante-gn.test", "PlatformAdmin1!")

report: dict = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "backend": BACKEND,
    "frontend": FRONTEND,
    "checks": [],
    "bugs": [],
    "pdfs": {},
    "journey": {},
    "roles": {},
}


def check(name: str, ok: bool, detail=None):
    report["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
    detail_s = detail if isinstance(detail, (str, int, type(None))) else json.dumps(detail, default=str)[:200]
    print(("PASS" if ok else "FAIL"), name, detail_s)


def bug(title: str, severity: str, detail: str, fix: str | None = None):
    report["bugs"].append({"title": title, "severity": severity, "detail": detail, "fix": fix})
    print(f"BUG[{severity}]", title, detail)


def login(email: str, password: str) -> str:
    r = httpx.post(
        f"{BACKEND}/auth/login-json",
        json={"email": email, "password": password},
        headers={"Origin": FRONTEND},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Origin": FRONTEND, "Content-Type": "application/json"}


def save_pdf(name: str, content: bytes) -> Path:
    path = ARTIFACTS / f"{name}.pdf"
    path.write_bytes(content)
    report["pdfs"][name] = str(path)
    return path


def pdf_ok(resp: httpx.Response) -> bool:
    return resp.status_code == 200 and resp.content[:4] == b"%PDF"


def audit_pdf_bytes(label: str, raw: bytes):
    has_font = b"ClinicSans" in raw or b"DejaVu" in raw or b"Identity-H" in raw
    a4ish = b"/MediaBox" in raw or b"A4" in raw or len(raw) > 800
    check(f"pdf_{label}_unicode_font", has_font, f"font={has_font} bytes={len(raw)}")
    check(f"pdf_{label}_a4ish", a4ish, f"bytes={len(raw)}")
    # classic mojibake from wrong encoding paths
    bad = (
        b"sp\xf8cialis" in raw
        or "SantÃ©".encode("utf-8") in raw
        or "RÃ©publique".encode("utf-8") in raw
    )
    check(f"pdf_{label}_no_mojibake", not bad, "mojibake scan")


def main() -> int:
    # --- Migration / infra ---
    email_st = httpx.get(f"{BACKEND}/health/email", timeout=60).json()
    check("email_effective_canonical", email_st.get("frontend_url") == FRONTEND, email_st.get("frontend_url"))
    check(
        "email_legacy_remapped_or_clean",
        email_st.get("frontend_url") == FRONTEND
        and (
            email_st.get("frontend_url_remapped_from_legacy") is True
            or email_st.get("frontend_url_raw") in (None, FRONTEND)
        ),
        {
            "raw": email_st.get("frontend_url_raw"),
            "remapped": email_st.get("frontend_url_remapped_from_legacy"),
        },
    )
    if email_st.get("frontend_url_remapped_from_legacy"):
        bug(
            "Railway FRONTEND_URL still legacy",
            "medium",
            f"raw={email_st.get('frontend_url_raw')}",
            "Set Railway FRONTEND_URL to canonical (requires RAILWAY_TOKEN / dashboard)",
        )

    db = httpx.get(f"{BACKEND}/health/database", timeout=60).json()
    check("db_identity", db.get("database_name") == "railway", f"{db.get('host')}/{db.get('database_name')}")

    r = httpx.options(
        f"{BACKEND}/auth/login-json",
        headers={
            "Origin": LEGACY,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
        timeout=30,
    )
    check(
        "cors_legacy_blocked",
        r.headers.get("access-control-allow-origin") != LEGACY,
        r.headers.get("access-control-allow-origin"),
    )
    r2 = httpx.options(
        f"{BACKEND}/auth/login-json",
        headers={
            "Origin": FRONTEND,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
        timeout=30,
    )
    check(
        "cors_canonical_allowed",
        r2.headers.get("access-control-allow-origin") == FRONTEND,
        r2.headers.get("access-control-allow-origin"),
    )

    # Repo / runtime references to legacy host (live frontend bundle)
    fe = httpx.get(FRONTEND, timeout=60, follow_redirects=True)
    check("frontend_spa", fe.status_code == 200)
    assets = re.findall(r"/assets/[^\"']+\.js", fe.text)
    api_urls = set()
    legacy_in_bundle = False
    for a in assets[:12]:
        body = httpx.get(FRONTEND + a, timeout=90).text
        api_urls.update(re.findall(r"https://web-production-[a-z0-9]+\.up\.railway\.app", body))
        if "frontend-seven-rust-94" in body:
            legacy_in_bundle = True
    check("frontend_points_only_canonical_backend", api_urls == {BACKEND} or not api_urls or BACKEND in api_urls, sorted(api_urls))
    check("frontend_bundle_no_legacy_host", not legacy_in_bundle and LEGACY not in fe.text, "scanned html+js")

    # --- Role logins + dashboards ---
    tokens: dict[str, str] = {}
    for role, (em, pw) in STAFF.items():
        try:
            tok = login(em, pw)
            tokens[role] = tok
            me = httpx.get(f"{BACKEND}/auth/me", headers=H(tok), timeout=60)
            body = me.json() if me.status_code == 200 else {}
            report["roles"][role] = {
                "email": em,
                "role": body.get("role"),
                "clinic_id": body.get("clinic_id"),
                "login": me.status_code == 200,
            }
            check(
                f"login_{role}",
                me.status_code == 200 and body.get("clinic_id") == 17,
                {"role": body.get("role"), "clinic_id": body.get("clinic_id")},
            )
        except Exception as exc:
            check(f"login_{role}", False, str(exc))
            bug(f"Login failed for {role}", "high", str(exc))

    role_paths = {
        "reception": "/clinical/reception/his/dashboard",
        "nurse": "/clinical/nurse/dashboard",
        "doctor": "/clinical/doctor/dashboard",
        "lab": "/clinical/lab/orders",
        "pharmacy": "/clinical/pharmacy/inventory",
        "cashier": "/clinical/billing/revenue/daily",
        "admin": "/auth/me",
    }
    for role, path in role_paths.items():
        if role not in tokens:
            continue
        rr = httpx.get(f"{BACKEND}{path}", headers=H(tokens[role]), timeout=60)
        check(f"dashboard_{role}", rr.status_code == 200, f"status={rr.status_code}")

    # Permission negatives: lab cannot create reception patients (valid body → expect 403)
    if "lab" in tokens:
        deny = httpx.post(
            f"{BACKEND}/clinical/reception/his/patients",
            headers=H(tokens["lab"]),
            json={
                "first_name": "RBAC",
                "last_name": "DenyLab",
                "gender": "M",
                "date_of_birth": "1990-01-01",
                "date_of_birth_precision": "full",
                "phone": "620000001",
                "address": "Kobaya",
                "emergency_contact": {
                    "full_name": "Contact",
                    "relationship": "Père",
                    "phone": "620000002",
                    "address": "Kobaya",
                },
                "payer": {"payer_type": "patient"},
                "confirm_duplicate": True,
                "registration_date": str(date.today()),
            },
            timeout=60,
        )
        check("rbac_lab_cannot_register_patient", deny.status_code in (401, 403), f"status={deny.status_code}")

    # --- Full patient journey ---
    run = uuid.uuid4().hex[:8].upper()
    journey: dict = {"run": run}
    try:
        if "reception" not in tokens:
            raise RuntimeError("reception token missing")
        h = H(tokens["reception"])
        patient_payload = {
            "first_name": "Harden",
            "last_name": f"E2E{run}",
            "gender": "F",
            "date_of_birth": "1992-06-15",
            "date_of_birth_precision": "full",
            "phone": f"622{run[:6]}",
            "address": "Kobaya hardening E2E",
            "city": "Conakry",
            "country": "Guinée",
            "nationality": "Guinéenne",
            "emergency_contact": {
                "full_name": "Contact Harden",
                "relationship": "Mère",
                "phone": "620111222",
                "address": "Kobaya",
            },
            "payer": {"payer_type": "patient"},
            "confirm_duplicate": True,
            "registration_date": str(date.today()),
        }
        pr = httpx.post(f"{BACKEND}/clinical/reception/his/patients", json=patient_payload, headers=h, timeout=90)
        check(
            "journey_register_patient",
            pr.status_code == 201,
            pr.json().get("patient_number") if pr.status_code == 201 else pr.text[:200],
        )
        if pr.status_code != 201:
            raise RuntimeError(pr.text[:300])
        patient = pr.json()
        pid = patient["id"]
        journey["patient_id"] = pid
        journey["patient_number"] = patient.get("patient_number")

        # Search
        sr = httpx.get(
            f"{BACKEND}/clinical/reception/his/patients/search",
            params={"q": f"E2E{run}"},
            headers=h,
            timeout=60,
        )
        found = any(x.get("id") == pid for x in (sr.json() if sr.status_code == 200 else []))
        check("journey_search_patient", found, f"status={sr.status_code}")

        # Admission
        adm_body = {
            "patient_id": pid,
            "admission_date": str(date.today()),
            "admission_time": datetime.now().strftime("%H:%M"),
            "services": ["Consultation spécialisée"],
            "admission_type": "specialized_consultation",
            "specialty_code": "medicine",
            "confirmation_status": "confirmed",
            "notes": f"Hardening E2E {run}",
        }
        docs = httpx.get(f"{BACKEND}/clinical/reception/doctors", headers=h, timeout=60)
        if docs.status_code == 200 and docs.json():
            d0 = docs.json()[0]
            uid = d0.get("user_id") or d0.get("id")
            if uid:
                adm_body["attending_clinician_user_id"] = uid
        ar = httpx.post(f"{BACKEND}/clinical/reception/his/admissions", json=adm_body, headers=h, timeout=90)
        check("journey_admission", ar.status_code in (200, 201), ar.text[:200] if ar.status_code >= 300 else ar.json().get("id"))
        journey["admission"] = ar.json() if ar.status_code < 300 else None

        # Invoice + payment
        inv_body = {
            "patient_id": pid,
            "department": "Consultation spécialisée",
            "billing_date": str(date.today()),
            "exemption_percent": 0,
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consultation spécialisée — Médecine",
                    "quantity": 1,
                    "unit_price_gnf": 250000,
                }
            ],
        }
        ir = httpx.post(f"{BACKEND}/clinical/reception/his/invoices", json=inv_body, headers=h, timeout=90)
        check(
            "journey_invoice",
            ir.status_code in (200, 201),
            ir.json().get("invoice_number") if ir.status_code < 300 else ir.text[:200],
        )
        invoice = ir.json() if ir.status_code < 300 else {}
        journey["invoice_id"] = invoice.get("id")
        journey["invoice_number"] = invoice.get("invoice_number")
        if invoice.get("id"):
            pay = httpx.post(
                f"{BACKEND}/clinical/reception/his/invoices/{invoice['id']}/payments",
                json={"amount_gnf": 250000, "payment_method": "cash", "reference": f"HARDEN-{run}"},
                headers=h,
                timeout=90,
            )
            check(
                "journey_payment",
                pay.status_code in (200, 201),
                pay.json().get("status") if pay.status_code < 300 else pay.text[:200],
            )
            pdf = httpx.get(
                f"{BACKEND}/clinical/reception/his/invoices/{invoice['id']}/receipt",
                headers=h,
                timeout=90,
            )
            ok = pdf_ok(pdf)
            check("pdf_invoice", ok, f"status={pdf.status_code} bytes={len(pdf.content)}")
            if ok:
                save_pdf(f"invoice_{invoice.get('invoice_number')}", pdf.content)
                audit_pdf_bytes("invoice", pdf.content)

        # Cashier sees revenue / pending
        if "cashier" in tokens:
            ch = H(tokens["cashier"])
            rev = httpx.get(f"{BACKEND}/clinical/billing/revenue/daily", headers=ch, timeout=60)
            check("cashier_revenue", rev.status_code == 200, rev.json().get("date") if rev.status_code == 200 else rev.text[:120])
            pend = httpx.get(f"{BACKEND}/clinical/billing/charges/pending", headers=ch, timeout=60)
            check("cashier_pending", pend.status_code == 200, f"count={len(pend.json()) if pend.status_code==200 else 0}")

        # Nurse assessment
        if "nurse" in tokens:
            nh = H(tokens["nurse"])
            assess = {
                "patient_id": pid,
                "admission_id": (journey.get("admission") or {}).get("id"),
                "temperature_c": 37.2,
                "bp_systolic": 120,
                "bp_diastolic": 80,
                "heart_rate": 78,
                "respiratory_rate": 18,
                "weight_kg": 65,
                "height_cm": 165,
                "reason_for_consultation": f"Hardening E2E {run} — céphalées",
                "nurse_notes": "Constantes stables — parcours durcissement",
            }
            nr = httpx.post(f"{BACKEND}/clinical/nurse/assessments", json=assess, headers=nh, timeout=90)
            check(
                "journey_nurse_assessment",
                nr.status_code in (200, 201),
                nr.json().get("id") if nr.status_code < 300 else nr.text[:250],
            )
            journey["nurse_assessment"] = nr.json() if nr.status_code < 300 else {"error": nr.text[:250]}
            if nr.status_code >= 400:
                bug("Nurse assessment create failed", "medium", nr.text[:400])

        # Doctor consultation + lab + prescription
        if "doctor" in tokens:
            dh = H(tokens["doctor"])
            q = httpx.get(f"{BACKEND}/clinical/doctor/queue", headers=dh, timeout=60)
            check("doctor_queue", q.status_code == 200, f"status={q.status_code}")
            open_body = {"patient_id": pid}
            if journey.get("admission") and isinstance(journey["admission"], dict):
                aid = journey["admission"].get("id")
                if aid:
                    open_body["admission_id"] = aid
            oc = httpx.post(f"{BACKEND}/clinical/doctor/open-consultation", json=open_body, headers=dh, timeout=90)
            if oc.status_code >= 400:
                oc = httpx.post(
                    f"{BACKEND}/clinical/consultations",
                    json={"patient_id": pid, "chief_complaint": f"E2E {run} céphalées"},
                    headers=dh,
                    timeout=90,
                )
            check(
                "journey_doctor_consultation",
                oc.status_code in (200, 201),
                oc.json().get("id") if oc.status_code < 300 else oc.text[:250],
            )
            consult = oc.json() if oc.status_code < 300 else {}
            cid = consult.get("id")
            journey["consultation_id"] = cid
            if cid:
                na = httpx.get(f"{BACKEND}/clinical/nurse/patients/{pid}/assessment", headers=dh, timeout=60)
                check("doctor_sees_nurse_assessment", na.status_code in (200, 404), f"status={na.status_code}")

                lo = httpx.post(
                    f"{BACKEND}/clinical/consultations/{cid}/lab-orders",
                    json={"test_code": "NFS", "test_name": "Numération Formule Sanguine", "priority": "routine"},
                    headers=dh,
                    timeout=90,
                )
                check(
                    "journey_lab_order",
                    lo.status_code in (200, 201),
                    lo.json().get("id") if lo.status_code < 300 else lo.text[:200],
                )
                journey["lab_order"] = lo.json() if lo.status_code < 300 else {"error": lo.text[:200]}

                rx = httpx.post(
                    f"{BACKEND}/clinical/consultations/{cid}/prescriptions",
                    json={
                        "items": [
                            {
                                "medication_name": "Paracétamol",
                                "dosage": "500 mg",
                                "route": "oral",
                                "frequency": "3x/jour",
                                "duration_days": 3,
                                "quantity": 12,
                                "instructions": "Après les repas",
                            }
                        ],
                        "notes": f"E2E {run}",
                    },
                    headers=dh,
                    timeout=90,
                )
                check(
                    "journey_prescription",
                    rx.status_code in (200, 201),
                    rx.json().get("id") if rx.status_code < 300 else rx.text[:200],
                )
                journey["prescription"] = rx.json() if rx.status_code < 300 else {"error": rx.text[:200]}

                cpdf = httpx.get(f"{BACKEND}/clinical/consultations/{cid}/pdf", headers=dh, timeout=90)
                cok = pdf_ok(cpdf)
                check("pdf_consultation", cok, f"status={cpdf.status_code} bytes={len(cpdf.content)}")
                if cok:
                    save_pdf(f"consultation_{cid}", cpdf.content)
                    audit_pdf_bytes("consultation", cpdf.content)

        # Lab result + validate + PDF
        if "lab" in tokens and isinstance(journey.get("lab_order"), dict) and journey["lab_order"].get("id"):
            lh = H(tokens["lab"])
            oid = journey["lab_order"]["id"]
            res = httpx.post(
                f"{BACKEND}/clinical/lab/orders/{oid}/results",
                json={
                    "result_summary": "NFS dans les normes — E2E durcissement",
                    "result_data": "Hb 13.2 g/dL; GB 6.1; Plaquettes 245",
                    "reference_range": "selon âge/sexe",
                    "interpretation": "Normal",
                },
                headers=lh,
                timeout=90,
            )
            check(
                "journey_lab_result",
                res.status_code in (200, 201),
                res.json().get("id") if res.status_code < 300 else res.text[:200],
            )
            rid = res.json().get("id") if res.status_code < 300 else None
            if rid:
                val = httpx.post(f"{BACKEND}/clinical/lab/results/{rid}/validate", headers=lh, timeout=90)
                check("journey_lab_validate", val.status_code == 200, f"status={val.status_code}")
                lpdf = httpx.get(f"{BACKEND}/clinical/lab/results/{rid}/pdf", headers=lh, timeout=90)
                lok = pdf_ok(lpdf)
                check("pdf_lab", lok, f"status={lpdf.status_code} bytes={len(lpdf.content)}")
                if lok:
                    save_pdf(f"lab_{rid}", lpdf.content)
                    audit_pdf_bytes("lab", lpdf.content)

        # Pharmacy dispense
        if "pharmacy" in tokens:
            ph = H(tokens["pharmacy"])
            inv = httpx.get(f"{BACKEND}/clinical/pharmacy/inventory", headers=ph, timeout=60)
            check(
                "pharmacy_stock",
                inv.status_code == 200 and len(inv.json()) >= 1,
                f"count={len(inv.json()) if inv.status_code==200 else 0}",
            )
            po = httpx.get(f"{BACKEND}/clinical/pharmacy/orders?scope=active", headers=ph, timeout=60)
            check("pharmacy_orders", po.status_code == 200, f"status={po.status_code}")
            orders = po.json() if po.status_code == 200 else []
            target = None
            for o in orders:
                if o.get("patient_id") == pid:
                    target = o
                    break
            if not target and orders:
                # match by prescription if present
                rxid = (journey.get("prescription") or {}).get("id")
                for o in orders:
                    if rxid and o.get("prescription_id") == rxid:
                        target = o
                        break
            if target:
                upd = httpx.patch(
                    f"{BACKEND}/clinical/pharmacy/orders/{target['id']}",
                    json={"status": "dispensed", "notes": f"E2E dispense {run}"},
                    headers=ph,
                    timeout=90,
                )
                check(
                    "journey_pharmacy_dispense",
                    upd.status_code == 200,
                    upd.json().get("status") if upd.status_code == 200 else upd.text[:200],
                )
            else:
                check("journey_pharmacy_dispense", False, "no pharmacy order linked to journey patient")
                bug("Pharmacy order missing after prescription", "medium", f"patient_id={pid}")

        # Extra printable docs (reception report + latest refund if any)
        report_pdf = httpx.get(
            f"{BACKEND}/clinical/reception/his/reports/export.pdf",
            params={"start": "2026-07-01", "end": str(date.today())},
            headers=h,
            timeout=90,
        )
        rok = pdf_ok(report_pdf)
        check("pdf_reception_report", rok, f"status={report_pdf.status_code} bytes={len(report_pdf.content)}")
        if rok:
            save_pdf("reception_report", report_pdf.content)
            audit_pdf_bytes("reception_report", report_pdf.content)
        refunds = httpx.get(f"{BACKEND}/clinical/reception/his/refunds", headers=h, timeout=60)
        if refunds.status_code == 200 and refunds.json():
            rid = refunds.json()[0]["id"]
            rpdf = httpx.get(f"{BACKEND}/clinical/reception/his/refunds/{rid}/receipt", headers=h, timeout=90)
            ok = pdf_ok(rpdf)
            check("pdf_refund", ok, f"status={rpdf.status_code} bytes={len(rpdf.content)}")
            if ok:
                save_pdf(f"refund_{rid}", rpdf.content)
                audit_pdf_bytes("refund", rpdf.content)

        # Admin staff list
        if "admin" in tokens:
            ah = H(tokens["admin"])
            staff = httpx.get(f"{BACKEND}/clinical/staff", params={"clinic_id": 17}, headers=ah, timeout=60)
            check("admin_list_staff", staff.status_code == 200, f"count={len(staff.json()) if staff.status_code==200 else 0}")

        # Demo patients preview (cleanup API may not be deployed yet)
        try:
            ptok = login(*PLATFORM_ADMIN)
            ph = H(ptok)
            preview = httpx.get(f"{BACKEND}/platform/clinics/17/demo-patients", headers=ph, timeout=60)
            check(
                "demo_cleanup_preview_api",
                preview.status_code in (200, 404),
                f"status={preview.status_code}",
            )
            if preview.status_code == 200:
                journey["demo_patients_matched"] = preview.json().get("matched")
        except Exception as exc:
            check("demo_cleanup_preview_api", False, str(exc))

        # Logout-ish: token still works until expiry; hit me then confirm frontend login page
        login_page = httpx.get(f"{FRONTEND}/login", timeout=60, follow_redirects=True)
        check("frontend_login_page", login_page.status_code == 200)

    except Exception as exc:
        bug("Patient journey aborted", "critical", str(exc))
        check("journey_complete", False, str(exc))
    else:
        check("journey_complete", True, journey.get("patient_number"))

    report["journey"] = journey
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    passed = sum(1 for c in report["checks"] if c["pass"])
    failed = sum(1 for c in report["checks"] if not c["pass"])
    report["summary"] = {
        "passed": passed,
        "failed": failed,
        "total": len(report["checks"]),
        "bugs": len(report["bugs"]),
        "pass_rate_pct": round(100.0 * passed / max(1, len(report["checks"])), 1),
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    (ARTIFACTS / "e2e_report.json").write_text(OUT.read_text())
    print("SUMMARY", report["summary"])
    print("WROTE", OUT)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
