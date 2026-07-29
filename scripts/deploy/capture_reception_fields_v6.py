#!/usr/bin/env python3
"""Production proof — editable registration date + populated patient fields."""
from __future__ import annotations
import os

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
EMAIL = "baldoumar14@gmail.com"
PASSWORD = os.environ["AASMA_RECEPTION_PASSWORD"]
RUN_ID = str(int(time.time()))[-6:]
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/reception-his-fields-v6"
OUT.mkdir(parents=True, exist_ok=True)


def login(page, path: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload(wait_until="networkidle")
    page.locator("#email").fill(EMAIL)
    page.locator("#password").fill(PASSWORD)
    page.click("button.login-submit")
    page.wait_for_function(
        "() => Boolean(sessionStorage.getItem('token') || sessionStorage.getItem('access_token'))",
        timeout=120000,
    )
    page.wait_for_function(
        "() => !window.location.pathname.includes('/login')",
        timeout=120000,
    )
    if path not in page.url:
        page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(3000)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 1100})
        page = ctx.new_page()

        login(page, "/clinical/reception")
        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.wait_for_timeout(500)

        reg_date = page.locator('label:has-text("Date inscription") input')
        if not reg_date.is_editable():
            raise RuntimeError("Date inscription must be editable")
        reg_date.fill("2026-01-10")
        dossier = page.locator('label:has-text("N° dossier patient") input').first
        if dossier.input_value().strip():
            raise RuntimeError("Dossier must be empty before save")
        page.screenshot(path=str(OUT / "01-registration-editable-date.png"), full_page=True)

        page.get_by_role("textbox", name="Nom *", exact=True).fill(f"Urgent{RUN_ID}")
        page.get_by_role("textbox", name="Prénom *", exact=True).fill(f"Fix{RUN_ID}")
        page.get_by_role("textbox", name="Date naissance *", exact=True).fill("1991-04-22")
        page.get_by_role("textbox", name="Tél. principal *", exact=True).fill(f"626{RUN_ID}")
        page.get_by_role("textbox", name="Adresse *", exact=True).fill("Kaloum")
        page.get_by_role("textbox", name="Nom du contact *", exact=True).fill("Contact")
        page.get_by_role("textbox", name="Téléphone *", exact=True).fill(f"627{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(4000)
        patient_id = dossier.input_value().strip()
        if not patient_id.startswith("PAT-"):
            raise RuntimeError(f"Expected generated dossier, got {patient_id!r}")
        if reg_date.input_value() != "2026-01-10":
            raise RuntimeError("Registration date not preserved in form")
        page.screenshot(path=str(OUT / "02-registration-dossier-generated.png"), full_page=True)

        # Search another existing patient to verify population via search
        page.locator("#patient-search").fill(patient_id)
        page.get_by_role("button", name="Rechercher").first.click()
        page.wait_for_timeout(2000)
        page.locator(".reception-his-search-results button").first.click()
        page.wait_for_timeout(1500)

        page.locator(".reception-his-tabs button", has_text="Admission").click()
        page.wait_for_timeout(800)
        dossier_adm = page.locator('fieldset:has(legend:text("Admission")) label:has-text("N° dossier patient") input')
        if dossier_adm.input_value().strip() != patient_id:
            raise RuntimeError(f"Admission dossier not populated: {dossier_adm.input_value()!r}")
        if not page.locator(".reception-his-patient-context--active .reception-his-value-filled").count():
            raise RuntimeError("Admission patient context not populated")
        page.screenshot(path=str(OUT / "03-admission-patient-populated.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Facturation").click()
        page.wait_for_timeout(800)
        dossier_bill = page.locator('fieldset:has(legend:text("Facture")) label:has-text("N° dossier patient") input')
        if dossier_bill.input_value().strip() != patient_id:
            raise RuntimeError(f"Billing dossier not populated: {dossier_bill.input_value()!r}")
        page.screenshot(path=str(OUT / "04-billing-patient-populated.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Remboursement").click()
        page.wait_for_timeout(800)
        dossier_ref = page.locator('fieldset:has(legend:text("Demande de remboursement")) label:has-text("N° dossier patient") input')
        if dossier_ref.input_value().strip() != patient_id:
            raise RuntimeError(f"Refund dossier not populated: {dossier_ref.input_value()!r}")
        page.screenshot(path=str(OUT / "05-refund-patient-populated.png"), full_page=True)

        page.close()
        ctx.close()
        browser.close()
    print(f"Screenshots saved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
