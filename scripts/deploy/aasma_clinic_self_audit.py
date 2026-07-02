#!/usr/bin/env python3
"""Production self-audit for AASMA clinic feedback (Reception, Lab, Pharmacy)."""

from __future__ import annotations

import json
import re
import sys
import time
import uuid
from datetime import date
from pathlib import Path

import httpx

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"

CREDS = {
    "reception": ("baldoumar14@gmail.com", "AasmaRecep1!"),
    "lab": ("mamadoudianbarry06@gmail.com", "AasmaLab1!"),
    "pharmacy": ("ben752231@gmail.com", "AasmaPharm1!"),
}


def login(email: str, password: str) -> dict:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": email, "password": password}, timeout=90)
    r.raise_for_status()
    return r.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def fetch_frontend_bundle() -> str:
    html = httpx.get(f"{FRONTEND}/", timeout=60, follow_redirects=True).text
    index_match = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
    if not index_match:
        return html
    index = httpx.get(f"{FRONTEND}{index_match.group(1)}", timeout=60).text
    m = re.search(r"clinical-pages-[A-Za-z0-9_-]+\.js", index)
    if not m:
        return index
    clinical = httpx.get(f"{FRONTEND}/assets/{m.group(0)}", timeout=90).text
    return index + "\n" + clinical


def main() -> int:
    report: dict = {"reception": [], "lab": [], "pharmacy": [], "frontend": []}
    run = uuid.uuid4().hex[:6]

    # --- Frontend bundle checks ---
    bundle = fetch_frontend_bundle()
    report["frontend"].append(("clinical bundle loaded", bool(bundle), ""))
    if bundle:
        report["lab"].append(("Pus sample type in bundle", "Pus" in bundle and "pus" in bundle, ""))
        report["lab"].append(("Écouvillon removed", "Écouvillon" not in bundle, ""))
        report["lab"].append(("Hémogramme template title", "Hémogramme (Mindray BC-10)" in bundle, ""))
        report["lab"].append(("BU template title", "Biochimie des urines (BU)" in bundle, ""))
        report["lab"].append(("ECBU template title", "Examen Cytobactériologique" in bundle, ""))
        report["lab"].append(
            ("Template selector UI",
             "Modèles de rapport officiels" in bundle or "lab-his-template-picker" in bundle,
             ""),
        )
        report["reception"].append(("Demandes de service tab", "Demandes de service" in bundle, ""))
        report["reception"].append(("Registration print", "Imprimer la fiche" in bundle, ""))
        report["reception"].append(("Relation Père", "Père" in bundle, ""))
        report["reception"].append(("Consultation spécialisée admission type", "specialized_consultation" in bundle, ""))
        report["reception"].append(("Nurse dashboard in bundle", "Tableau de bord — Infirmier" in bundle or "/clinical/nurse" in bundle, ""))
        report["reception"].append(("Nurse assessment save label", "Enregistrer l'évaluation" in bundle or "Enregistrer l\\'évaluation" in bundle, ""))

    # --- Reception API workflow ---
    try:
        tok = login(*CREDS["reception"])["access_token"]
        h = auth_headers(tok)
        suffix = run
        reg_payload = {
            "first_name": f"Audit{suffix}",
            "last_name": "Patient",
            "date_of_birth": "1990-05-15",
            "gender": "M",
            "address": "Kobaya test",
            "phone": f"620{suffix[:6]}",
            "registration_date": str(date.today()),
            "emergency_contact": {
                "full_name": "Contact Test",
                "relationship": "Père",
                "phone": f"621{suffix[:6]}",
            },
            "payer": {"payer_type": "patient"},
        }
        r = httpx.post(f"{BACKEND}/clinical/reception/his/patients", json=reg_payload, headers=h, timeout=90)
        ok_reg = r.status_code in (200, 201)
        report["reception"].append(("Register patient API", ok_reg, r.text[:200] if not ok_reg else ""))
        patient = r.json() if ok_reg else {}
        pid = patient.get("id")
        report["reception"].append(("Patient saved with id", bool(pid), str(patient.get("patient_number", ""))))

        if pid:
            r2 = httpx.get(f"{BACKEND}/clinical/reception/his/patients/{pid}", headers=h, timeout=60)
            report["reception"].append(("Patient retrievable", r2.status_code == 200, ""))

            adm = httpx.post(
                f"{BACKEND}/clinical/reception/his/admissions",
                json={
                    "patient_id": pid,
                    "admission_date": str(date.today()),
                    "admission_time": "10:00:00",
                    "services": ["Consultation spécialisée — Pédiatrie", "Laboratoire"],
                    "admission_type": "specialized_consultation",
                    "confirmation_status": "confirmed",
                },
                headers=h,
                timeout=90,
            )
            report["reception"].append(
                ("Admission specialized_consultation", adm.status_code in (200, 201), adm.text[:200]),
            )

            cat = httpx.get(f"{BACKEND}/clinical/reception/his/billing-catalog", headers=h, timeout=60)
            catalog = cat.json() if cat.status_code == 200 else {}
            lab_test = (catalog.get("laboratory_tests") or [{}])[0]
            inv = httpx.post(
                f"{BACKEND}/clinical/reception/his/invoices",
                json={
                    "patient_id": pid,
                    "department": "Laboratoire",
                    "items": [
                        {
                            "charge_type": "laboratory",
                            "description": f"Hémogramme (Mindray BC-10) ({lab_test.get('code', 'HEMO')})",
                            "quantity": 1,
                            "unit_price_gnf": lab_test.get("price_gnf", 50000),
                            "source_type": "reception",
                        }
                    ],
                    "exemption_percent": 0,
                    "billing_date": str(date.today()),
                },
                headers=h,
                timeout=90,
            )
            ok_inv = inv.status_code in (200, 201)
            report["reception"].append(("Create invoice", ok_inv, inv.text[:200] if not ok_inv else ""))
            invoice = inv.json() if ok_inv else {}
            iid = invoice.get("id")
            remaining = invoice.get("remaining_balance_gnf", 0)

            if iid:
                pay1 = httpx.post(
                    f"{BACKEND}/clinical/reception/his/invoices/{iid}/payments",
                    json={"amount_gnf": max(1, remaining // 2), "payment_method": "cash", "reference": "AUDIT1"},
                    headers=h,
                    timeout=90,
                )
                pay2 = httpx.post(
                    f"{BACKEND}/clinical/reception/his/invoices/{iid}/payments",
                    json={
                        "amount_gnf": max(0, remaining - remaining // 2),
                        "payment_method": "orange_money",
                        "reference": "AUDIT2",
                    },
                    headers=h,
                    timeout=90,
                )
                report["reception"].append(("Split payment line 1", pay1.status_code in (200, 201), pay1.text[:120]))
                report["reception"].append(("Split payment line 2", pay2.status_code in (200, 201), pay2.text[:120]))

                pdf = httpx.get(
                    f"{BACKEND}/clinical/reception/his/invoices/{iid}/receipt",
                    headers=h,
                    timeout=90,
                )
                is_pdf = pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
                report["reception"].append(("Invoice PDF receipt", is_pdf, f"status={pdf.status_code} len={len(pdf.content)}"))
    except Exception as e:
        report["reception"].append(("Reception workflow exception", False, str(e)))

    # --- Lab API workflow ---
    try:
        tok = login(*CREDS["lab"])["access_token"]
        h = auth_headers(tok)
        if pid:
            sr = httpx.get(f"{BACKEND}/clinical/lab/patients/{pid}/service-requests", headers=h, timeout=90)
            rows = sr.json() if sr.status_code == 200 else []
            report["lab"].append(("Service requests visible", sr.status_code == 200 and len(rows) > 0, f"count={len(rows)}"))
            order_id = rows[0].get("lab_order_id") if rows else None
            if order_id:
                res = httpx.post(
                    f"{BACKEND}/clinical/lab/orders/{order_id}/results",
                    json={
                        "result_summary": "GB: 5.2",
                        "result_data": json.dumps(
                            {
                                "rows": [{"parameter": "GB", "result": "5.2", "reference": "4-10", "unit": "10^9/L"}],
                                "validation": {
                                    "technician": "Tech Audit",
                                    "validation_date": str(date.today()),
                                    "validation_time": "11:00",
                                },
                                "template_id": "hemogram",
                            }
                        ),
                    },
                    headers=h,
                    timeout=90,
                )
                report["lab"].append(("Save lab results", res.status_code in (200, 201), res.text[:200]))
                rid = res.json().get("id") if res.status_code in (200, 201) else None
                if rid:
                    val = httpx.post(f"{BACKEND}/clinical/lab/results/{rid}/validate", headers=h, timeout=90)
                    report["lab"].append(("Validate lab result", val.status_code in (200, 201), val.text[:120]))
                    time.sleep(2)
                    pdf = httpx.get(f"{BACKEND}/clinical/lab/results/{rid}/pdf", headers=h, timeout=90)
                    is_pdf = pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
                    has_template = False
                    try:
                        from pypdf import PdfReader
                        import io
                        text = "".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf.content)).pages)
                        has_template = "Mindray" in text or "Biochimie des urines" in text or "ECBU" in text
                    except Exception:
                        has_template = b"Mindray" in pdf.content
                    report["lab"].append(("Lab report PDF", is_pdf, f"len={len(pdf.content)}"))
                    report["lab"].append(("Lab PDF uses official template", has_template, ""))
            else:
                report["lab"].append(("Lab order from service request", False, "no lab_order_id"))
    except Exception as e:
        report["lab"].append(("Lab workflow exception", False, str(e)))

    # --- Pharmacy API workflow ---
    try:
        tok = login(*CREDS["pharmacy"])["access_token"]
        h = auth_headers(tok)
        if pid:
            search = httpx.get(
                f"{BACKEND}/clinical/pharmacy/patients/search",
                params={"q": patient.get("patient_number") or str(pid)},
                headers=h,
                timeout=90,
            )
            hits = search.json() if search.status_code == 200 else []
            report["pharmacy"].append(("Patient search", search.status_code == 200 and len(hits) > 0, f"hits={len(hits)}"))
        inv = httpx.get(f"{BACKEND}/clinical/pharmacy/inventory", headers=h, timeout=90)
        report["pharmacy"].append(("Stock inventory API", inv.status_code == 200, f"items={len(inv.json()) if inv.status_code==200 else 0}"))
        report["pharmacy"].append(("Stock tab in frontend bundle", "Stock" in bundle, ""))
    except Exception as e:
        report["pharmacy"].append(("Pharmacy workflow exception", False, str(e)))

    # --- Nurse API workflow ---
    report["nurse"] = []
    try:
        admin = login("contactpolycliniqueaasma@gmail.com", "AasmaAdmin1!")
        ah = auth_headers(admin["access_token"])
        dash = httpx.get(f"{BACKEND}/clinical/nurse/dashboard", headers=ah, timeout=60)
        report["nurse"].append(("Nurse dashboard API", dash.status_code == 200, dash.text[:120]))
        if pid:
            save = httpx.post(
                f"{BACKEND}/clinical/nurse/assessments",
                headers=ah,
                json={
                    "patient_id": pid,
                    "temperature_c": 37.5,
                    "bp_systolic": 120,
                    "bp_diastolic": 80,
                    "heart_rate": 78,
                    "respiratory_rate": 16,
                    "height_cm": 170,
                    "weight_kg": 65,
                    "reason_for_consultation": f"Audit nurse {run}",
                    "allergies": "Test audit",
                    "nurse_notes": "Audit overnight",
                },
                timeout=90,
            )
            report["nurse"].append(("Save nurse assessment API", save.status_code in (200, 201), save.text[:160]))
            if save.status_code in (200, 201):
                body = save.json()
                report["nurse"].append(("BMI calculated server-side", body.get("bmi") is not None, str(body.get("bmi"))))
                get = httpx.get(f"{BACKEND}/clinical/nurse/patients/{pid}/assessment", headers=ah, timeout=60)
                report["nurse"].append(("Retrieve nurse assessment", get.status_code == 200, get.text[:120]))
    except Exception as e:
        report["nurse"].append(("Nurse workflow exception", False, str(e)))

    # Print report
    def section_pass(name: str, items: list) -> bool:
        print(f"\n=== {name} ===")
        all_ok = True
        for label, ok, detail in items:
            status = "PASS" if ok else "FAIL"
            if not ok:
                all_ok = False
            extra = f" — {detail}" if detail else ""
            print(f"  [{status}] {label}{extra}")
        return all_ok

    rec_pass = section_pass("RECEPTION", report["reception"])
    lab_pass = section_pass("LABORATORY", report["lab"])
    pharm_pass = section_pass("PHARMACY", report["pharmacy"])
    nurse_pass = section_pass("NURSE", report.get("nurse", []))
    section_pass("FRONTEND BUNDLE", report["frontend"])

    print("\n=== SUMMARY ===")
    print(f"Reception: {'PASS' if rec_pass else 'FAIL'}")
    print(f"Laboratory: {'PASS' if lab_pass else 'FAIL'}")
    print(f"Pharmacy: {'PASS' if pharm_pass else 'FAIL'}")
    print(f"Nurse: {'PASS' if nurse_pass else 'FAIL'}")

    out = Path(__file__).resolve().parents[2] / "docs" / "AASMA_SELF_AUDIT.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0 if rec_pass and lab_pass and pharm_pass and nurse_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
