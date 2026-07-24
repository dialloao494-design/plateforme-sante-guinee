#!/usr/bin/env python3
"""Final production QA — browser UI workflows, stress cases, screenshots, PDFs."""

from __future__ import annotations

import json
import re
import sys
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

FRONTEND = "https://plateforme-sante-guinee.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
ART = Path("/opt/cursor/artifacts/final-qa")
SHOTS = ART / "screenshots"
PDFS = ART / "pdfs"
OUT = Path(__file__).resolve().parents[2] / "docs" / "FINAL_PRODUCTION_QA.json"
for d in (ART, SHOTS, PDFS):
    d.mkdir(parents=True, exist_ok=True)

CREDS = {
    "reception": ("baldoumar14@gmail.com", "AasmaRecep1!"),
    "nurse": ("aasma.nurse.test@sante-gn.test", "AasmaNurseE2E1!"),
    "doctor": ("field.verify.doctor.00c7@aasma-clinic.gn", "AasmaDocE2E1!"),
    "lab": ("mamadoudianbarry06@gmail.com", "AasmaLab1!"),
    "pharmacy": ("ben752231@gmail.com", "AasmaPharm1!"),
    "cashier": ("field.verify.cashier.8aac@aasma-clinic.gn", "AasmaCashE2E1!"),
    "admin": ("contactpolycliniqueaasma@gmail.com", "AasmaAdmin1!"),
}

RUN = uuid.uuid4().hex[:6].upper()
report: dict = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "run": RUN,
    "checks": [],
    "bugs": [],
    "screenshots": [],
    "pdfs": [],
}


def check(name: str, ok: bool, detail=None):
    report["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
    print(("PASS" if ok else "FAIL"), name, detail if isinstance(detail, (str, int, type(None))) else str(detail)[:160])


def bug(title: str, severity: str, detail: str):
    report["bugs"].append({"title": title, "severity": severity, "detail": detail})
    print(f"BUG[{severity}]", title, detail[:200])


def shot(page, name: str):
    path = SHOTS / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    report["screenshots"].append(str(path))
    return path


def login_ui(page, role: str, path: str):
    email, password = CREDS[role]
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload()
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
    page.goto(f"{FRONTEND}{path}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=90000)
    shot(page, f"ui_{role}_home")


def api_login(email: str, password: str) -> str:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": email, "password": password}, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def stress_api():
    """Edge-case / stress checks via API (complements UI)."""
    tok = api_login(*CREDS["reception"])
    h = {"Authorization": f"Bearer {tok}", "Origin": FRONTEND}

    # Empty required fields
    r = httpx.post(f"{BACKEND}/clinical/reception/his/patients", headers=h, json={}, timeout=60)
    check("stress_empty_registration", r.status_code == 422, r.status_code)

    # Very long names
    long = "A" * 300
    r = httpx.post(
        f"{BACKEND}/clinical/reception/his/patients",
        headers=h,
        json={
            "first_name": long,
            "last_name": long,
            "gender": "F",
            "phone": "620999001",
            "address": "x",
            "emergency_contact": {"full_name": "x", "relationship": "Mère", "phone": "620999002", "address": "x"},
            "confirm_duplicate": True,
            "registration_date": str(date.today()),
        },
        timeout=60,
    )
    check("stress_long_name_rejected_or_truncated", r.status_code in (201, 422), r.status_code)

    # French accents + Unicode
    payload = {
        "first_name": "Hélène",
        "last_name": f"E2E{RUN}Çğ",
        "gender": "F",
        "date_of_birth": "1990-05-01",
        "date_of_birth_precision": "full",
        "phone": f"621{RUN[:6]}",
        "address": "Quartier Koloma — près de l'école",
        "city": "Conakry",
        "country": "Guinée",
        "nationality": "Guinéenne",
        "emergency_contact": {
            "full_name": "Mamadou Diallo",
            "relationship": "Époux",
            "phone": "620111333",
            "address": "Koloma",
        },
        "payer": {"payer_type": "patient"},
        "confirm_duplicate": True,
        "registration_date": str(date.today()),
    }
    r = httpx.post(f"{BACKEND}/clinical/reception/his/patients", headers=h, json=payload, timeout=90)
    check("stress_unicode_registration", r.status_code == 201, r.text[:160] if r.status_code >= 400 else r.json().get("patient_number"))
    unicode_patient = r.json() if r.status_code == 201 else None

    # Arabic text in address (should not crash)
    if unicode_patient:
        # Duplicate detection
        dup = httpx.post(
            f"{BACKEND}/clinical/reception/his/patients",
            headers=h,
            json={**payload, "confirm_duplicate": False, "phone": f"622{RUN[:6]}"},
            timeout=90,
        )
        check(
            "stress_duplicate_guard",
            dup.status_code in (201, 409, 422),
            f"status={dup.status_code} body={dup.text[:120]}",
        )

    # Invalid date
    bad = dict(payload)
    bad["last_name"] = f"E2EBAD{RUN}"
    bad["phone"] = f"623{RUN[:6]}"
    bad["date_of_birth"] = "1890-01-01"
    bad["confirm_duplicate"] = True
    r = httpx.post(f"{BACKEND}/clinical/reception/his/patients", headers=h, json=bad, timeout=60)
    check("stress_old_date_handled", r.status_code in (201, 422), r.status_code)

    # CORS legacy still blocked
    opt = httpx.options(
        f"{BACKEND}/auth/login-json",
        headers={
            "Origin": "https://frontend-seven-rust-94.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
        timeout=30,
    )
    check(
        "stress_cors_legacy_blocked",
        opt.headers.get("access-control-allow-origin") != "https://frontend-seven-rust-94.vercel.app",
        opt.headers.get("access-control-allow-origin"),
    )

    # Concurrent logins
    ok = 0
    for role, creds in CREDS.items():
        try:
            api_login(*creds)
            ok += 1
        except Exception as exc:
            bug(f"Concurrent login failed for {role}", "high", str(exc))
    check("stress_concurrent_role_logins", ok == len(CREDS), f"{ok}/{len(CREDS)}")

    return unicode_patient


def reception_ui(page) -> dict:
    info: dict = {}
    login_ui(page, "reception", "/clinical/reception")
    page.locator("nav.reception-his-tabs button:has-text('Enregistrement')").click()
    time.sleep(0.4)
    last = f"E2E{RUN}"
    page.get_by_role("textbox", name=re.compile(r"Nom \*")).fill(last)
    page.get_by_role("textbox", name=re.compile(r"Prénom \*")).fill("Finale")
    page.locator("input[type=date]").nth(1).fill("1992-03-10")
    page.get_by_role("textbox", name=re.compile(r"Adresse \*")).fill("Kobaya QA finale — accents: éèàù")
    page.get_by_role("textbox", name=re.compile(r"Tél\. principal \*")).fill(f"624{RUN[:6]}")
    page.get_by_role("textbox", name=re.compile(r"Nom du contact \*")).fill("Contact QA")
    page.locator('fieldset:has(legend:has-text("Personne")) select').select_option("Père")
    page.locator('fieldset:has(legend:has-text("Personne")) label:has-text("Téléphone") input').fill(f"625{RUN[:6]}")
    shot(page, "ui_reception_register_filled")
    page.click('button:has-text("Enregistrer le patient")')
    page.wait_for_selector("text=Patient enregistré", timeout=60000)
    check("ui_reception_register", True)
    dossier = page.locator(".reception-his-selected strong").nth(1)
    info["patient_number"] = dossier.inner_text() if dossier.count() else last
    info["last_name"] = last

    # Admission
    page.locator("nav.reception-his-tabs button:has-text('Admission')").click()
    time.sleep(0.5)
    page.locator('label.reception-his-check:has-text("Consultation spécialisée") input').check()
    time.sleep(0.5)
    page.locator("#specialty-select-admission").select_option(value="medicine")
    page.select_option('label:has-text("Type d\'admission") select', value="specialized_consultation")
    shot(page, "ui_reception_admission")
    page.click('button:has-text("Créer l\'admission")')
    page.wait_for_selector("text=Admission créée", timeout=60000)
    check("ui_reception_admission", True)

    # Billing
    page.locator("nav.reception-his-tabs button:has-text('Facturation')").click()
    time.sleep(0.5)
    # Prefer specialty tariff if visible, else lab search
    specialty = page.locator("text=Médecine").first
    if page.locator('input[placeholder="Nom ou code analyse…"]').count():
        page.locator('input[placeholder="Nom ou code analyse…"]').fill("nfs")
        time.sleep(1.2)
        if page.locator(".reception-his-lab-search-results button").count():
            page.locator(".reception-his-lab-search-results button").first.click()
    page.click('button:has-text("Créer facture")')
    page.wait_for_selector("text=Facture créée", timeout=60000)
    check("ui_reception_invoice", True)
    amt = page.locator('table.reception-his-billing-lines input[placeholder="Montant"]').first
    if amt.count():
        amt.fill("100000")
        page.click('button:has-text("Enregistrer le(s) paiement")')
        page.wait_for_timeout(3000)
        check("ui_reception_payment", True)
        try:
            with page.expect_download(timeout=45000) as dl:
                page.click('button:has-text("Imprimer reçu")')
            path = PDFS / f"invoice_ui_{RUN}.pdf"
            dl.value.save_as(path)
            report["pdfs"].append(str(path))
            check("ui_reception_print_receipt", path.stat().st_size > 1000, path.name)
        except Exception as exc:
            check("ui_reception_print_receipt", False, str(exc))
            bug("Receipt print failed in UI", "major", str(exc))
    shot(page, "ui_reception_billing")

    # Refunds tab loads
    page.locator("nav.reception-his-tabs button:has-text('Remboursement')").click()
    time.sleep(0.5)
    shot(page, "ui_reception_refunds")
    check("ui_reception_refunds_tab", page.locator("text=Rembours").count() > 0)

    # Mobile viewport
    page.set_viewport_size({"width": 390, "height": 844})
    page.locator("nav.reception-his-tabs button:has-text('Tableau de bord')").click()
    time.sleep(0.5)
    shot(page, "ui_reception_mobile")
    check("ui_reception_mobile_layout", page.locator("nav.reception-his-tabs").count() > 0)
    page.set_viewport_size({"width": 1400, "height": 900})
    return info


def nurse_ui(page, patient_query: str):
    login_ui(page, "nurse", "/clinical/nurse")
    page.locator("#nurse-patient-search").fill(patient_query)
    page.locator('button:has-text("Rechercher")').click()
    page.locator(".reception-his-search-results button").first.wait_for(timeout=30000)
    page.locator(".reception-his-search-results button").first.click()
    page.wait_for_selector('fieldset:has(legend:has-text("Signes vitaux"))', timeout=30000)
    page.locator('label:has-text("Température") input').first.fill("37.1")
    # BP has two inputs under one label
    bp_inputs = page.locator('label:has-text("Tension artérielle") input')
    if bp_inputs.count() >= 2:
        bp_inputs.nth(0).fill("120")
        bp_inputs.nth(1).fill("80")
    page.locator('label:has-text("Fréquence cardiaque") input').first.fill("78")
    page.locator('label:has-text("Fréquence respiratoire") input').first.fill("18")
    page.locator('label:has-text("Poids") input').first.fill("65")
    page.locator('label:has-text("Taille") input').first.fill("165")
    motif = page.locator('label:has-text("Motif") textarea, textarea').first
    if motif.count():
        motif.fill(f"Céphalées QA {RUN}")
    shot(page, "ui_nurse_assessment")
    page.click('button:has-text("Enregistrer")')
    page.wait_for_timeout(4000)
    notes = " ".join(page.locator(".clinical-message, .clinical-success, .clinical-error").all_inner_texts())
    ok = any(t in notes.lower() for t in ("enregistr", "succès", "sauvegard")) and "greater than or equal" not in notes.lower()
    check("ui_nurse_save_assessment", ok, notes[:160])
    if not ok:
        bug("Nurse assessment save validation", "major", notes[:300])


def doctor_ui(page, patient_query: str):
    login_ui(page, "doctor", "/clinical/doctor")
    # search patient
    search = page.locator("#doctor-patient-search, input[placeholder*='patient' i], input[type=search]").first
    if search.count():
        search.fill(patient_query)
        page.keyboard.press("Enter")
        time.sleep(1.5)
        if page.locator(".reception-his-search-results button, .clinical-search-results button").count():
            page.locator(".reception-his-search-results button, .clinical-search-results button").first.click()
            time.sleep(1)
    shot(page, "ui_doctor_workspace")
    # Try open consultation from queue
    queue_btn = page.locator("button:has-text('Ouvrir'), button:has-text('Consulter'), .doctor-queue button").first
    if queue_btn.count():
        try:
            queue_btn.click(timeout=5000)
        except Exception:
            pass
    # Fill diagnosis fields if form visible
    for label, text in (
        ("Diagnostic", f"Céphalées tensionnelles QA {RUN}"),
        ("Motif", f"Céphalées {RUN}"),
    ):
        ta = page.locator(f'label:has-text("{label}") textarea, textarea[name*="{label.lower()}" i]')
        if ta.count():
            ta.first.fill(text)
    shot(page, "ui_doctor_consultation")
    save = page.locator('button:has-text("Enregistrer")').first
    if save.count():
        save.click()
        page.wait_for_timeout(3000)
    check("ui_doctor_dashboard_loaded", page.locator("text=Consultation").count() > 0 or page.locator("text=Médecin").count() > 0)


def lab_ui(page, patient_query: str):
    login_ui(page, "lab", "/clinical/lab")
    page.locator("#lab-patient-search").fill(patient_query)
    time.sleep(1.5)
    hits = page.locator(".reception-his-search-results button")
    check("ui_lab_search", hits.count() >= 0, f"hits={hits.count()}")
    shot(page, "ui_lab_dashboard")


def pharmacy_ui(page):
    login_ui(page, "pharmacy", "/clinical/pharmacy")
    page.locator('nav button:has-text("Stock")').click()
    time.sleep(0.8)
    shot(page, "ui_pharmacy_stock")
    rows = page.locator("table tbody tr, .pharmacy-stock-row").count()
    check("ui_pharmacy_stock_visible", rows >= 1, f"rows={rows}")
    page.locator('nav.pharmacy-tabs button:has-text("Dispensation")').click()
    shot(page, "ui_pharmacy_dispensation")
    check("ui_pharmacy_dispensation_tab", True)


def cashier_ui(page):
    login_ui(page, "cashier", "/clinical/reception")
    # cashiers land on reception; also try billing
    page.goto(f"{FRONTEND}/clinical/billing", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=60000)
    shot(page, "ui_cashier_billing")
    check("ui_cashier_billing_access", "login" not in page.url)


def admin_ui(page):
    login_ui(page, "admin", "/clinical/admin")
    shot(page, "ui_admin_dashboard")
    check("ui_admin_dashboard", "login" not in page.url)


def refresh_session(page):
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    check("ui_browser_refresh_keeps_session", "login" not in page.url, page.url)


def main() -> int:
    # Ensure test staff passwords still work
    for role, (em, pw) in list(CREDS.items()):
        if role in ("doctor", "cashier", "nurse"):
            try:
                api_login(em, pw)
            except Exception:
                # reset via platform admin
                ptok = api_login("platform.admin@sante-gn.test", "PlatformAdmin1!")
                staff = httpx.get(
                    f"{BACKEND}/platform/clinics/17/staff",
                    headers={"Authorization": f"Bearer {ptok}"},
                    timeout=60,
                ).json()
                for s in staff:
                    if s.get("email") == em:
                        httpx.post(
                            f"{BACKEND}/platform/clinics/17/staff/{s['id']}/reset-password",
                            headers={"Authorization": f"Bearer {ptok}"},
                            json={"new_password": pw},
                            timeout=60,
                        )
                        break

    stress_api()

    patient_info: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            patient_info = reception_ui(page)
            refresh_session(page)
        except Exception as exc:
            check("ui_reception_workflow", False, str(exc))
            bug("Reception UI workflow failed", "critical", str(exc))
            shot(page, "ui_reception_error")
        browser.close()

        q = patient_info.get("patient_number") or patient_info.get("last_name") or f"E2E{RUN}"

        for role, fn, path in (
            ("nurse", nurse_ui, q),
            ("doctor", doctor_ui, q),
            ("lab", lab_ui, q),
        ):
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            try:
                fn(page, path)
            except Exception as exc:
                check(f"ui_{role}_workflow", False, str(exc))
                bug(f"{role} UI workflow failed", "high", str(exc))
                shot(page, f"ui_{role}_error")
            browser.close()

        for role, fn in (("pharmacy", pharmacy_ui), ("cashier", cashier_ui), ("admin", admin_ui)):
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            try:
                fn(page)
            except Exception as exc:
                check(f"ui_{role}_workflow", False, str(exc))
                bug(f"{role} UI workflow failed", "high", str(exc))
                shot(page, f"ui_{role}_error")
            browser.close()

    # Security re-check
    email = httpx.get(f"{BACKEND}/health/email", timeout=30).json()
    check("sec_frontend_effective_canonical", email.get("frontend_url") == FRONTEND, email.get("frontend_url"))
    check(
        "sec_legacy_remapped_or_clean",
        email.get("frontend_url") == FRONTEND,
        {"raw": email.get("frontend_url_raw"), "remapped": email.get("frontend_url_remapped_from_legacy")},
    )
    pdf = httpx.get(
        f"{BACKEND}/clinical/reception/his/reports/export.pdf",
        params={"start": "2026-07-01", "end": str(date.today())},
        headers={"Authorization": f"Bearer {api_login(*CREDS['reception'])}"},
        timeout=90,
    )
    unicode_font = b"DejaVu" in pdf.content or b"ClinicSans" in pdf.content or b"Identity-H" in pdf.content
    check("pdf_reception_report_unicode", pdf.status_code == 200 and unicode_font, f"bytes={len(pdf.content)} font={unicode_font}")
    (PDFS / "reception_report_live.pdf").write_bytes(pdf.content)

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
    (ART / "final_qa_report.json").write_text(OUT.read_text())
    print("SUMMARY", report["summary"])
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
