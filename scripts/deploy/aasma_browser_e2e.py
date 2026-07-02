#!/usr/bin/env python3
"""Full browser E2E clinic workflow — AASMA production."""

from __future__ import annotations

import json
import re
import sys
import time
import uuid
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"

CREDS = {
    "reception": ("baldoumar14@gmail.com", "AasmaRecep1!"),
    "lab": ("mamadoudianbarry06@gmail.com", "AasmaLab1!"),
    "pharmacy": ("ben752231@gmail.com", "AasmaPharm1!"),
}

RUN = uuid.uuid4().hex[:6]
PATIENT = {
    "last_name": f"E2E{RUN}",
    "first_name": "Clinic",
    "phone": f"622{uuid.uuid4().hex[:7]}",
    "dob": "1992-03-10",
}


def login(page, email: str, password: str, expect_path: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload()
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
    page.goto(f"{FRONTEND}{expect_path}", wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle", timeout=90000)


def click_tab(page, label: str) -> None:
    page.locator(f"nav.reception-his-tabs button:has-text('{label}')").click()
    time.sleep(0.4)


def main() -> int:
    report: dict[str, list] = {
        "reception": [],
        "admission": [],
        "billing": [],
        "laboratory": [],
        "pharmacy": [],
    }
    patient_number = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # --- RECEPTION: Register ---
        try:
            login(page, *CREDS["reception"], "/clinical/reception")
            click_tab(page, "Enregistrement")
            page.get_by_role("textbox", name=re.compile(r"Nom \*")).fill(PATIENT["last_name"])
            page.get_by_role("textbox", name=re.compile(r"Prénom \*")).fill(PATIENT["first_name"])
            page.locator('label:has-text("Date naissance") input').fill(PATIENT["dob"])
            page.get_by_role("textbox", name=re.compile(r"Adresse \*")).fill("Kobaya test E2E")
            page.get_by_role("textbox", name=re.compile(r"Tél. principal \*")).fill(PATIENT["phone"])
            page.get_by_role("textbox", name=re.compile(r"Nom du contact \*")).fill("Contact E2E")
            page.locator('fieldset:has(legend:has-text("Personne")) select').select_option("Père")
            page.locator('fieldset:has(legend:has-text("Personne")) input[type="tel"], fieldset:has(legend:has-text("Personne")) label:has-text("Téléphone") input').fill(f"623{RUN[:6]}")
            page.click('button:has-text("Enregistrer le patient")')
            page.wait_for_selector("text=Patient enregistré", timeout=60000)
            report["reception"].append(("Register patient", True, ""))

            print_btn = page.locator('button:has-text("Imprimer la fiche")')
            report["reception"].append(("Registration print button", print_btn.count() > 0, ""))
            if print_btn.count():
                print_btn.click()
                time.sleep(0.5)

            # patient active banner
            dossier_el = page.locator(".reception-his-selected strong").nth(1)
            patient_number = dossier_el.inner_text() if dossier_el.count() else ""
            report["reception"].append(("Patient saved visible", bool(patient_number), patient_number))
        except Exception as e:
            report["reception"].append(("Register workflow", False, str(e)))

        # --- ADMISSION ---
        try:
            click_tab(page, "Admission")
            page.locator('label.reception-his-check:has-text("Consultation spécialisée") input').check()
            page.locator("#specialty-select-admission").select_option(label="Pédiatrie")
            page.select_option('label:has-text("Type d\'admission") select', value="specialized_consultation")
            time.sleep(0.3)
            specialty_val = page.locator("#specialty-select-admission").input_value()
            report["admission"].append(("Admission layout services section", page.locator(".reception-his-admission-services").count() > 0, ""))
            report["admission"].append(("Specialty picker on admission type", specialty_val == "pediatrics", specialty_val))
            page.click('button:has-text("Créer l\'admission")')
            page.wait_for_selector("text=Admission créée", timeout=60000)
            report["admission"].append(("Create admission", True, ""))
        except Exception as e:
            report["admission"].append(("Admission workflow", False, str(e)))

        # --- BILLING ---
        try:
            click_tab(page, "Facturation")
            page.locator('input[placeholder="Nom ou code analyse…"]').fill("hémogramme")
            time.sleep(1.2)
            lab_btn = page.locator(".reception-his-lab-search-results button")
            if lab_btn.count() == 0:
                page.locator('input[placeholder="Nom ou code analyse…"]').fill("nfs")
                time.sleep(1.2)
            page.locator(".reception-his-lab-search-results button").first.click(timeout=15000)
            page.click('button:has-text("Créer facture")')
            page.wait_for_selector("text=Facture créée", timeout=60000)
            report["billing"].append(("Create invoice", True, ""))

            amt_input = page.locator('table.reception-his-billing-lines input[placeholder="Montant"]').first
            remaining_hint = page.locator("text=Reste à payer").locator("..").locator(".reception-his-amount-display, .reception-his-auto-display").last
            amt_input.fill("100000")
            page.click('button:has-text("Enregistrer le(s) paiement")')
            page.wait_for_selector("text=Paiement", timeout=60000)
            report["billing"].append(("Payment entry", True, ""))

            with page.expect_download(timeout=60000) as dl_info:
                page.click('button:has-text("Imprimer reçu")')
            download = dl_info.value
            pdf_path = Path(__file__).resolve().parents[2] / "docs" / f"e2e_invoice_{RUN}.pdf"
            download.save_as(pdf_path)
            from pypdf import PdfReader
            pdf_text = "".join((p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages)
            has_brand = "CHFMP" in pdf_text and "AASMA" in pdf_text
            no_poly = "POLYCLINIQUE" not in pdf_text
            no_square = "■" not in pdf_text and "980■" not in pdf_text
            report["billing"].append(("Invoice PDF branding CHFMP – AASMA", has_brand and no_poly, str(pdf_path.name)))
            report["billing"].append(("Invoice PDF no corrupted amounts", no_square, ""))
        except Exception as e:
            report["billing"].append(("Billing workflow", False, str(e)))

        browser.close()

        # --- LAB (separate session) ---
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            login(page, *CREDS["lab"], "/clinical/lab")
            page.locator("#lab-patient-search").fill(patient_number or PATIENT["last_name"])
            time.sleep(1.5)
            page.locator(".reception-his-search-results button").first.click()
            time.sleep(2)
            saisir = page.locator('button:has-text("Saisir résultats")')
            report["laboratory"].append(("Service requests from reception", saisir.count() > 0, f"buttons={saisir.count()}"))
            saisir.first.click(timeout=30000)
            page.locator('button:has-text("Hémogramme (Mindray BC-10)")').click()
            time.sleep(0.3)
            report["laboratory"].append(("Template picker visible", page.locator('button:has-text("Hémogramme (Mindray BC-10)")').count() > 0, ""))
            page.locator(".lab-his-results-table tbody tr").first.locator("input").nth(1).fill("5.1")
            page.locator('label:has-text("Biologiste") input').fill("Tech E2E")
            page.locator('.lab-his-status-options input[type="radio"]').nth(2).check(force=True)
            validated = False
            joined = ""
            for attempt in range(6):
                page.click('button:has-text("Enregistrer les résultats")')
                page.wait_for_timeout(8000 + attempt * 2000)
                notes = page.locator(".clinical-message, .clinical-success, .clinical-error").all_inner_texts()
                joined = " | ".join(notes)
                if any(
                    token in joined
                    for token in ("Résultats validés", "Résultats enregistrés", "vous pouvez imprimer")
                ):
                    validated = True
                    break
                if any(
                    token in joined.lower()
                    for token in ("impossible de joindre", "erreur", "échec", "introuvable")
                ):
                    time.sleep(2 + attempt)
                    continue
                if attempt < 5:
                    time.sleep(2 + attempt)
                    continue
                break
            report["laboratory"].append(("Validate results in browser", validated, joined[:160]))
            if not validated:
                raise RuntimeError(joined or "Lab validation failed")
            time.sleep(1)
            print_btn = page.locator(".lab-his-validation-actions button.clinical-btn--secondary")
            report["laboratory"].append(("Print report button visible", print_btn.count() > 0, f"count={print_btn.count()}"))
            if print_btn.count():
                print_btn.scroll_into_view_if_needed()
                with page.expect_download(timeout=60000) as dl_info:
                    print_btn.click()
                lab_pdf = Path(__file__).resolve().parents[2] / "docs" / f"e2e_lab_{RUN}.pdf"
                dl_info.value.save_as(lab_pdf)
                from pypdf import PdfReader
                lab_text = "".join((p.extract_text() or "") for p in PdfReader(str(lab_pdf)).pages)
                report["laboratory"].append(("Lab PDF Mindray template", "Mindray" in lab_text, lab_pdf.name))
            else:
                report["laboratory"].append(("Lab PDF print in browser", False, "Print button not shown after validate"))
        except Exception as e:
            report["laboratory"].append(("Lab workflow", False, str(e)))

        browser.close()

        # --- PHARMACY ---
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        try:
            login(page, *CREDS["pharmacy"], "/clinical/pharmacy")
            page.locator('nav button:has-text("Stock")').click()
            report["pharmacy"].append(("Stock tab", page.locator('h2:has-text("Stock")').count() > 0 or page.locator("text=Stock").count() > 0, ""))
            page.locator('nav.pharmacy-tabs button:has-text("Dispensation")').click()
            page.locator("#pharmacy-patient-search").fill(patient_number or PATIENT["last_name"])
            time.sleep(1)
            hits = page.locator(".reception-his-search-results button, .pharmacy-his-search-results button")
            report["pharmacy"].append(("Patient search", hits.count() > 0, f"hits={hits.count()}"))
            if hits.count():
                hits.first.click()
                report["pharmacy"].append(("Select patient", True, ""))
        except Exception as e:
            report["pharmacy"].append(("Pharmacy workflow", False, str(e)))

        browser.close()

    def summarize(name: str, items: list) -> bool:
        print(f"\n=== {name} ===")
        ok = True
        for label, passed, detail in items:
            status = "PASS" if passed else "FAIL"
            if not passed:
                ok = False
            extra = f" — {detail}" if detail else ""
            print(f"  [{status}] {label}{extra}")
        return ok

    r_ok = summarize("Reception", report["reception"])
    a_ok = summarize("Admission", report["admission"])
    b_ok = summarize("Billing", report["billing"])
    l_ok = summarize("Laboratory", report["laboratory"])
    p_ok = summarize("Pharmacy", report["pharmacy"])

    out = Path(__file__).resolve().parents[2] / "docs" / "AASMA_BROWSER_E2E.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0 if all([r_ok, a_ok, b_ok, l_ok, p_ok]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
