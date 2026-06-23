#!/usr/bin/env python3
"""Capture full AASMA laboratory UI workflow screenshots on production."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "ui_e2e_screenshots" / "aasma-lab-workflow"
FRONTEND = "https://frontend-seven-rust-94.vercel.app"
LAB_EMAIL = "mamadoudianbarry06@gmail.com"
LAB_PASSWORD = "AasmaLab1!"

EXPECTED_CATEGORIES = [
    "Hématologie",
    "Hémostase",
    "Biochimie",
    "Immuno-Sérologie",
    "Bactériologie",
    "Parasitologie",
    "Hormones",
    "Reproduction/Fertilité",
    "Marqueurs Cancéreux",
    "Autres examens",
]


def shot(page, name: str) -> str:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    page.screenshot(path=str(path), full_page=False)
    return str(path)


def login_lab(page) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload()
    page.locator("#email").fill(LAB_EMAIL)
    page.locator("#password").fill(LAB_PASSWORD)
    page.click("button.login-submit")
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
    page.wait_for_load_state("networkidle", timeout=90000)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            login_lab(page)
            page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(2000)
            shot(page, "01-laboratory-dashboard.png")

            page.get_by_role("button", name="Nouvelle demande", exact=True).click()
            page.wait_for_timeout(2500)
            body = page.inner_text("body")
            if "Informations patient" not in body:
                shot(page, "FAIL-old-ui.png")
                print("FAIL: production frontend still shows old laboratory UI")
                return 1

            shot(page, "02-nouvelle-demande-patient-block.png")

            missing = [c for c in EXPECTED_CATEGORIES if c not in body]
            if missing:
                print("FAIL missing categories in UI:", missing)
                shot(page, "FAIL-missing-categories.png")
                return 1

            page.locator(".lab-patient-panel").scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            shot(page, "03-patient-information-fields.png")

            page.locator('input[placeholder="Nom, téléphone ou ID"]').fill("Dashboard")
            page.get_by_role("button", name="Rechercher", exact=True).click()
            page.wait_for_timeout(2000)
            pick = page.locator(".clinical-list button").first
            if pick.count() == 0:
                page.locator('input[placeholder="Nom, téléphone ou ID"]').fill("246")
                page.get_by_role("button", name="Rechercher", exact=True).click()
                page.wait_for_timeout(2000)
            if page.locator(".clinical-list button").count() > 0:
                page.locator(".clinical-list button").first.click()
            else:
                page.locator('label:has-text("ID Patient")').locator("..").locator("input").fill("246")
                page.locator('label:has-text("ID Patient")').locator("..").locator("input").blur()
            page.wait_for_timeout(2000)
            shot(page, "04-patient-loaded.png")

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(800)
            shot(page, "05-catalog-bottom-autres-examens.png")
            page.screenshot(path=str(OUT / "06-all-categories-full-page.png"), full_page=True)

            gly_row = page.locator(".lab-catalog-row", has_text="Glycémie").first
            gly_row.scroll_into_view_if_needed()
            gly_row.locator('input[type="checkbox"]').check()
            gly_row.locator('input[placeholder="Prix GNF"]').fill("10000")
            shot(page, "07-exam-selected-with-price.png")

            page.get_by_role("button", name="Enregistrer la demande", exact=True).click()
            page.wait_for_timeout(3000)
            shot(page, "08-order-saved.png")

            page.get_by_role("button", name="En cours", exact=False).click()
            page.wait_for_timeout(2500)
            body_pending = page.inner_text("body")
            if "Glycémie" not in body_pending:
                print("FAIL: order not visible in En cours")
                shot(page, "FAIL-en-cours.png")
                return 1
            shot(page, "09-en-cours-order.png")

            page.get_by_role("button", name="Saisir résultat", exact=True).first.click()
            page.wait_for_timeout(1500)
            page.locator('textarea').first.fill("Glycémie à jeun : 0,92 g/L")
            page.locator('label:has-text("Valeurs de référence")').locator("..").locator("input").fill("0,70 – 1,10 g/L")
            page.locator('label:has-text("Interprétation")').locator("..").locator("textarea").fill("Normale")
            shot(page, "10-result-entry.png")

            page.get_by_role("button", name="Valider le résultat", exact=True).click()
            page.wait_for_timeout(3000)
            shot(page, "11-result-validated.png")

            page.get_by_role("button", name="Validés", exact=False).click()
            page.wait_for_timeout(2500)
            validated_body = page.inner_text("body")
            if "Glycémie" not in validated_body and "0,92" not in validated_body:
                print("FAIL: validated result not listed")
                shot(page, "FAIL-validated-tab.png")
                return 1
            shot(page, "12-validated-list.png")

            print(f"OK — workflow screenshots saved to {OUT}")
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
