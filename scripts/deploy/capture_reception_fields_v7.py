#!/usr/bin/env python3
"""Production proof — generated IDs and populated patient display fields."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
EMAIL = "baldoumar14@gmail.com"
PASSWORD = "AasmaRecep1!"
RUN_ID = str(int(time.time()))[-6:]
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/reception-his-fields-v7"
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
    page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(3000)


def field_text(page, legend: str, label: str) -> str:
    loc = page.locator(f'fieldset:has(legend:text("{legend}")) label:has-text("{label}") .reception-his-auto-display')
    return loc.first.inner_text().strip()


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 1100})
        page = ctx.new_page()

        login(page, "/clinical/reception")
        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.get_by_role("textbox", name="Nom *", exact=True).fill(f"Prod{RUN_ID}")
        page.get_by_role("textbox", name="Prénom *", exact=True).fill(f"Proof{RUN_ID}")
        page.get_by_role("textbox", name="Date naissance *", exact=True).fill("1989-08-20")
        page.get_by_role("textbox", name="Tél. principal *", exact=True).fill(f"628{RUN_ID}")
        page.get_by_role("textbox", name="Adresse *", exact=True).fill("Kaloum")
        page.get_by_role("textbox", name="Nom du contact *", exact=True).fill("Contact")
        page.get_by_role("textbox", name="Téléphone *", exact=True).fill(f"629{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(4500)

        banner = page.locator(".reception-his-generated-id strong").first
        patient_id = banner.inner_text().strip()
        if not patient_id.startswith("PAT-"):
            raise RuntimeError(f"Generated patient ID missing: {patient_id!r}")
        page.screenshot(path=str(OUT / "01-registration-generated-id.png"), full_page=True)

        page.locator("#patient-search").fill(patient_id)
        page.get_by_role("button", name="Rechercher").first.click()
        page.wait_for_timeout(2000)
        page.locator(".reception-his-search-results button").first.click(force=True)
        page.wait_for_timeout(1500)

        page.locator(".reception-his-tabs button", has_text="Admission").click()
        page.wait_for_timeout(800)
        dossier = field_text(page, "Admission", "N° dossier patient")
        name = field_text(page, "Admission", "Nom et prénom")
        if dossier != patient_id:
            raise RuntimeError(f"Admission dossier mismatch: {dossier!r}")
        if "Prod" not in name:
            raise RuntimeError(f"Admission name not populated: {name!r}")
        page.screenshot(path=str(OUT / "02-admission-patient-filled.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Facturation").click()
        page.wait_for_timeout(800)
        if field_text(page, "Facture", "N° dossier patient") != patient_id:
            raise RuntimeError("Billing dossier not populated")
        page.screenshot(path=str(OUT / "03-billing-patient-filled.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Remboursement").click()
        page.wait_for_timeout(800)
        if field_text(page, "Demande de remboursement", "N° dossier patient") != patient_id:
            raise RuntimeError("Refund dossier not populated")
        page.screenshot(path=str(OUT / "04-refund-patient-filled.png"), full_page=True)

        page.close()
        ctx.close()
        browser.close()
    print(f"Screenshots saved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
