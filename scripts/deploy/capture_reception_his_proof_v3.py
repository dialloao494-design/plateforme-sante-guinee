#!/usr/bin/env python3
"""Production screenshots — Reception UX fixes (empty dossier + inline patient search)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://frontend-seven-rust-94.vercel.app"
EMAIL = "baldoumar14@gmail.com"
PASSWORD = "AasmaRecep1!"
RUN_ID = str(int(time.time()))[-6:]
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/reception-his-proof-v3"
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
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()

        login(page, "/clinical/reception")

        # Registration — empty dossier before save
        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.wait_for_timeout(500)
        dossier = page.locator('label:has-text("N° dossier patient") input')
        if dossier.input_value().strip():
            raise RuntimeError(f"Dossier field should be empty before save, got: {dossier.input_value()!r}")
        page.screenshot(path=str(OUT / "01-registration-empty-dossier.png"), full_page=True)

        # Admission / Billing / Refund — inline search panels (no patient selected)
        for idx, tab_name, fname in [
            (2, "Admission", "02-admission-search-panel.png"),
            (3, "Facturation", "03-billing-search-panel.png"),
            (4, "Remboursement", "04-refund-search-panel.png"),
        ]:
            page.locator(".reception-his-tabs button", has_text=tab_name).click()
            page.wait_for_timeout(500)
            panel = page.locator(".reception-his-patient-search")
            if not panel.is_visible():
                raise RuntimeError(f"Patient search panel not visible on {tab_name} tab")
            if not page.get_by_role("button", name="Rechercher").first.is_visible():
                raise RuntimeError(f"Rechercher button not visible on {tab_name} tab")
            page.screenshot(path=str(OUT / fname), full_page=True)

        # Full registration workflow
        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.get_by_role("textbox", name="Nom *", exact=True).fill(f"Test{RUN_ID}")
        page.get_by_role("textbox", name="Prénom *", exact=True).fill(f"Recep{RUN_ID}")
        page.get_by_role("textbox", name="Date naissance *", exact=True).fill("1992-03-10")
        page.get_by_role("textbox", name="Tél. principal *", exact=True).fill(f"620{RUN_ID}")
        page.get_by_role("textbox", name="Adresse *", exact=True).fill("Kaloum, Conakry")
        page.get_by_role("textbox", name="Nom du contact *", exact=True).fill("Contact Urgence")
        page.get_by_role("textbox", name="Téléphone *", exact=True).fill(f"621{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(4000)
        patient_id = dossier.input_value().strip()
        if not patient_id.startswith("PAT-"):
            raise RuntimeError(f"Expected generated PAT ID, got: {patient_id!r}")
        page.screenshot(path=str(OUT / "05-registration-patient-id.png"), full_page=True)

        # Admission via inline search (mouse workflow)
        page.locator(".reception-his-tabs button", has_text="Admission").click()
        page.wait_for_timeout(300)
        page.locator(".reception-his-patient-search input").fill(patient_id)
        page.locator(".reception-his-patient-search button", has_text="Rechercher").click()
        page.wait_for_timeout(2000)
        page.locator(".reception-his-search-results--inline button").first.click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "06-admission-with-patient.png"), full_page=True)
        page.locator("button.clinical-btn", has_text="Créer l'admission").click()
        page.wait_for_timeout(3000)

        page.locator(".reception-his-tabs button", has_text="Facturation").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "07-billing-with-patient.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Tableau de bord").click()
        page.get_by_role("button", name="Actualiser").click()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "08-dashboard.png"), full_page=True)

        page.close()
        ctx.close()
        browser.close()
    print(f"Screenshots saved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
