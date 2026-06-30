#!/usr/bin/env python3
"""Capture production proof screenshots for /clinical/lab dashboard corrections."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
LAB_EMAIL = "mamadoudianbarry06@gmail.com"
LAB_PASSWORD = "AasmaLab1!"
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/lab-dashboard-proof"
OUT.mkdir(parents=True, exist_ok=True)


def login_lab(page):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.evaluate("localStorage.clear(); sessionStorage.clear()")
    page.reload(wait_until="networkidle")
    page.locator("#email").fill(LAB_EMAIL)
    page.locator("#password").fill(LAB_PASSWORD)
    page.click("button.login-submit")
    page.wait_for_function("() => Boolean(localStorage.getItem('token'))", timeout=120000)
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
    if "/clinical/lab" not in page.url:
        page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle")
    page.wait_for_selector(".lab-his-page", timeout=120000)
    page.wait_for_timeout(1500)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        login_lab(page)

        body_text = page.locator("body").inner_text()
        assert "Recettes du jour" not in body_text, "Recettes du jour still visible"
        assert "Recettes du mois" not in body_text, "Recettes du mois still visible"
        assert "Examens demandés" not in body_text or "Demandes de service" in body_text
        assert "Enregistrer la demande" not in body_text, "Billing submit still visible"

        page.screenshot(path=str(OUT / "01-lab-dashboard-stats.png"), full_page=True)

        demandes_visible = page.locator("h3", has_text="Demandes de service").count() > 0
        print("demandes_de_service_section:", demandes_visible)

        stat_btn = page.locator("button.clinical-stat-card", has_text="En attente").first
        stat_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "02-lab-stat-click-en-attente.png"), full_page=True)

        queue_panel = page.locator(".lab-his-queue-panel")
        print("queue_panel_visible:", queue_panel.count() > 0)

        page.locator("#lab-patient-search").fill("620")
        page.wait_for_timeout(2500)
        results = page.locator(".reception-his-search-results button")
        if results.count() > 0:
            results.first.click()
            page.wait_for_timeout(2000)
            page.screenshot(path=str(OUT / "03-lab-patient-demandes-service.png"), full_page=True)
            print("patient_selected:", True)
        else:
            print("patient_selected:", False)

        browser.close()
        print("OK — screenshots saved to", OUT)


if __name__ == "__main__":
    main()
