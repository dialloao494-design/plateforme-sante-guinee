#!/usr/bin/env python3
"""Production proof — full forms always visible on Admission/Billing/Refund."""
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
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/reception-his-forms-v5"
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


def assert_form_visible(page, title: str) -> None:
    if not page.locator("h2", has_text=title).is_visible():
        raise RuntimeError(f"Form title not visible: {title}")
    if page.locator(".reception-his-patient-search").count() > 0:
        raise RuntimeError(f"Search-only panel still visible on {title}")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 1100})
        page = ctx.new_page()

        login(page, "/clinical/reception")

        # No patient — forms must still be visible
        for tab, fname, title in [
            ("Admission", "01-admission-no-patient.png", "Admission"),
            ("Facturation", "02-billing-no-patient.png", "Facturation"),
            ("Remboursement", "03-refund-no-patient.png", "Remboursement"),
        ]:
            page.locator(".reception-his-tabs button", has_text=tab).click()
            page.wait_for_timeout(700)
            assert_form_visible(page, title)
            page.screenshot(path=str(OUT / fname), full_page=True)

        # Register + select patient
        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.get_by_role("textbox", name="Nom *", exact=True).fill(f"Proof{RUN_ID}")
        page.get_by_role("textbox", name="Prénom *", exact=True).fill(f"User{RUN_ID}")
        page.get_by_role("textbox", name="Date naissance *", exact=True).fill("1988-06-12")
        page.get_by_role("textbox", name="Tél. principal *", exact=True).fill(f"624{RUN_ID}")
        page.get_by_role("textbox", name="Adresse *", exact=True).fill("Kaloum")
        page.get_by_role("textbox", name="Nom du contact *", exact=True).fill("Contact")
        page.get_by_role("textbox", name="Téléphone *", exact=True).fill(f"625{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(3500)
        patient_id = page.locator('label:has-text("N° dossier patient") input').input_value().strip()
        if not patient_id.startswith("PAT-"):
            raise RuntimeError(f"Missing patient id after registration: {patient_id!r}")

        for tab, fname, title in [
            ("Admission", "04-admission-with-patient.png", "Admission"),
            ("Facturation", "05-billing-with-patient.png", "Facturation"),
            ("Remboursement", "06-refund-with-patient.png", "Remboursement"),
        ]:
            page.locator(".reception-his-tabs button", has_text=tab).click()
            page.wait_for_timeout(700)
            assert_form_visible(page, title)
            dossier = page.locator('label:has-text("N° dossier patient") input').first
            if dossier.input_value().strip() != patient_id:
                raise RuntimeError(f"Patient id not filled on {tab}: {dossier.input_value()!r}")
            page.screenshot(path=str(OUT / fname), full_page=True)

        page.close()
        ctx.close()
        browser.close()
    print(f"Screenshots saved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
