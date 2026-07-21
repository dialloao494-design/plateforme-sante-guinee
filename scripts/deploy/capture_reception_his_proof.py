#!/usr/bin/env python3
"""Production proof — Reception HIS workflow: Register → Admission → Billing → Refund → Dashboard."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

FRONTEND = "https://plateforme-sante-guinee.vercel.app"
EMAIL = "baldoumar14@gmail.com"
PASSWORD = "AasmaRecep1!"
RUN_ID = str(int(time.time()))[-6:]
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/reception-his-proof"
OUT.mkdir(parents=True, exist_ok=True)


def login(page) -> None:
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
    page.goto(f"{FRONTEND}/clinical/reception", wait_until="networkidle", timeout=120000)
    page.wait_for_selector("h1", timeout=60000)


def main() -> int:
    results = {"run_id": RUN_ID, "steps": []}
    video_dir = OUT / "video"
    video_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1280, "height": 900},
        )
        page = context.new_page()
        login(page)
        page.screenshot(path=str(OUT / "01-reception-dashboard.png"), full_page=True)
        results["steps"].append("dashboard_initial")

        # Registration tab
        page.get_by_role("button", name="Enregistrement").click()
        page.wait_for_timeout(500)
        first = f"Recep{RUN_ID}"
        last = f"Test{RUN_ID}"
        page.locator('label:has-text("Prénom") input').first.fill(first)
        page.locator('label:has-text("Nom") input').first.fill(last)
        page.locator('label:has-text("Tél. principal") input').first.fill(f"620{RUN_ID}")
        page.locator('label:has-text("Adresse") input').first.fill("Kaloum, Conakry")
        page.locator('label:has-text("Date naissance") input').first.fill("1990-05-15")
        page.locator('label:has-text("Nom complet") input').first.fill("Contact Urgence")
        page.locator('label:has-text("Téléphone") input').last.fill(f"621{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(4000)
        page.screenshot(path=str(OUT / "02-registration.png"), full_page=True)
        results["steps"].append("registration")

        # Admission (auto-switched or manual)
        if page.get_by_role("button", name="Admission").is_visible():
            page.get_by_role("button", name="Admission").click()
        page.wait_for_timeout(500)
        page.get_by_role("button", name="Créer l'admission").click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "03-admission.png"), full_page=True)
        results["steps"].append("admission")

        # Billing
        page.get_by_role("button", name="Facturation").click()
        page.wait_for_timeout(500)
        page.locator('label:has-text("Description") input').first.fill(f"Consultation {RUN_ID}")
        page.locator('label:has-text("Montant total") input').first.fill("150000")
        page.get_by_role("button", name="Créer facture").click()
        page.wait_for_timeout(3000)
        page.locator('label:has-text("Montant") input').first.fill("100000")
        page.get_by_role("button", name="Enregistrer paiement").click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "04-billing.png"), full_page=True)
        results["steps"].append("billing")

        # Refund
        page.get_by_role("button", name="Remboursement").click()
        page.wait_for_timeout(500)
        page.locator('label:has-text("Facture") select').first.select_option(index=1)
        page.locator('label:has-text("Service payé") input').first.fill("Consultation non consommée")
        page.locator('label:has-text("Montant consommé") input').first.fill("50000")
        page.locator('label:has-text("Montant remboursement") input').first.fill("50000")
        page.locator('label:has-text("Bénéficiaire") input').first.fill("Famille Test")
        page.locator('label:has-text("Tél. bénéficiaire") input').first.fill(f"622{RUN_ID}")
        page.get_by_role("button", name="Soumettre remboursement").click()
        page.wait_for_timeout(3000)
        page.get_by_role("button", name="Approuver").first.click()
        page.wait_for_timeout(2000)
        page.get_by_role("button", name="Marquer payé").first.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=str(OUT / "05-refund.png"), full_page=True)
        results["steps"].append("refund")

        # Dashboard refresh
        page.get_by_role("button", name="Tableau de bord").click()
        page.get_by_role("button", name="Actualiser").click()
        page.wait_for_timeout(3000)
        page.screenshot(path=str(OUT / "06-dashboard-updated.png"), full_page=True)
        results["steps"].append("dashboard_updated")

        page.close()
        context.close()
        browser.close()

    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Screenshots: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
