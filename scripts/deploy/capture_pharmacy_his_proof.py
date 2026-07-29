#!/usr/bin/env python3
"""Production proof — Pharmacy HIS dashboard (5 screenshots)."""
from __future__ import annotations

import os

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/pharmacy-his-proof"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
EMAIL, PWD = "ben752231@gmail.com", os.environ["AASMA_PHARMACY_PASSWORD"]
PATIENT_QUERY = "620231409"

MOCKUP_LINES = [
    ("Paracétamol", 1, 1000),
    ("Vitaler", 1, 20000),
    ("Doliprane", 2, 10000),
    ("Gant stérile", 2, 10000),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"frontend": FRONTEND, "screenshots": [], "steps": []}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})

        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
        page.locator("#email").fill(EMAIL)
        page.locator("#password").fill(PWD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/clinical/pharmacy", wait_until="networkidle", timeout=120000)
        page.wait_for_selector("h1:has-text('Tableau de bord Pharmacie')", timeout=60000)

        shot1 = OUT / "01-empty-search.png"
        page.screenshot(path=str(shot1), full_page=True)
        report["screenshots"].append(shot1.name)
        report["steps"].append("empty_search")

        search = page.locator("#pharmacy-patient-search")
        search.fill(PATIENT_QUERY)
        page.get_by_role("button", name="Rechercher", exact=True).click()
        page.wait_for_timeout(2500)
        result_btn = page.locator(".reception-his-search-results button").first
        if result_btn.count():
            result_btn.click()
            page.wait_for_timeout(1500)

        shot2 = OUT / "02-patient-selected.png"
        page.screenshot(path=str(shot2), full_page=True)
        report["screenshots"].append(shot2.name)
        report["steps"].append("patient_selected")

        rows = page.locator(".pharmacy-his-table tbody tr")
        for idx, (name, qty, price) in enumerate(MOCKUP_LINES):
            if idx >= rows.count():
                page.get_by_role("button", name="+ Ligne", exact=True).click()
            row = page.locator(".pharmacy-his-table tbody tr").nth(idx)
            row.locator("td").nth(0).locator("input").fill(name)
            row.locator("td").nth(1).locator("input").fill(str(qty))
            row.locator("td").nth(2).locator("input").fill(str(price))

        shot3 = OUT / "03-service-request-filled.png"
        page.screenshot(path=str(shot3), full_page=True)
        report["screenshots"].append(shot3.name)
        report["steps"].append("service_request_filled")

        page.get_by_role("button", name="Enregistrer la demande de service", exact=True).click()
        page.wait_for_timeout(4000)
        page.locator("h2", has_text="Facturation").scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        shot4 = OUT / "04-billing-payment-mode.png"
        page.screenshot(path=str(shot4), full_page=True)
        report["screenshots"].append(shot4.name)
        report["steps"].append("billing_payment_mode")

        print_btn = page.get_by_role("button", name="Imprimer reçu", exact=True)
        print_visible = print_btn.is_visible()
        bill_btn = page.get_by_role("button", name="Facturer le patient", exact=True)
        report["print_button_visible"] = print_visible
        report["bill_button_visible"] = bill_btn.is_visible()

        shot5 = OUT / "05-receipt-print-action.png"
        page.locator(".pharmacy-his-card--billing").screenshot(path=str(shot5))
        report["screenshots"].append(shot5.name)
        report["steps"].append("receipt_print_action")

        browser.close()

    proof = Path(__file__).resolve().parents[2] / "docs/PHARMACY_HIS_PRODUCTION_PROOF.json"
    proof.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
