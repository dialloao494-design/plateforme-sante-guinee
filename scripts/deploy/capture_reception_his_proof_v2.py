#!/usr/bin/env python3
"""Production screenshots — Reception HIS forms + AASMA reports (no Koloma)."""
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
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/reception-his-proof-v2"
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
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        video_dir = OUT / "video"
        video_dir.mkdir(exist_ok=True)
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1400, "height": 900},
        )
        page = ctx.new_page()

        login(page, "/clinical/reception")
        page.screenshot(path=str(OUT / "01-dashboard.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Enregistrement").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "02-registration-form.png"), full_page=True)

        page.get_by_role("textbox", name="Nom *", exact=True).fill(f"Test{RUN_ID}")
        page.get_by_role("textbox", name="Prénom *", exact=True).fill(f"Recep{RUN_ID}")
        page.get_by_role("textbox", name="Date naissance *", exact=True).fill("1992-03-10")
        page.get_by_role("textbox", name="Tél. principal *", exact=True).fill(f"620{RUN_ID}")
        page.get_by_role("textbox", name="Adresse *", exact=True).fill("Kaloum, Conakry")
        page.get_by_role("textbox", name="Nom du contact *", exact=True).fill("Contact Urgence")
        page.get_by_role("textbox", name="Téléphone *", exact=True).fill(f"621{RUN_ID}")
        page.get_by_role("button", name="Enregistrer le patient").click()
        page.wait_for_timeout(4000)
        page.screenshot(path=str(OUT / "03-registration-done.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Admission").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "04-admission-form.png"), full_page=True)
        page.locator("button.clinical-btn", has_text="Créer l'admission").click()
        page.wait_for_timeout(3000)

        page.locator(".reception-his-tabs button", has_text="Facturation").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "05-billing-form.png"), full_page=True)
        page.locator('label:has-text("Description") input').first.fill(f"Consultation {RUN_ID}")
        page.locator('label:has-text("Montant total") input').first.fill("200000")
        page.get_by_role("button", name="Créer facture").click()
        page.wait_for_timeout(2500)
        page.locator('label:has-text("Montant à encaisser") input').fill("100000")
        page.get_by_role("button", name="Enregistrer paiement").click()
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "06-billing-payment.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Remboursement").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "07-refund-form.png"), full_page=True)

        page.locator(".reception-his-tabs button", has_text="Tableau de bord").click()
        page.get_by_role("button", name="Actualiser").click()
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "08-dashboard-updated.png"), full_page=True)

        login(page, "/clinical/reports")
        page.screenshot(path=str(OUT / "09-reports-aasma.png"), full_page=True)
        body = page.inner_text("body")
        if "Koloma" in body:
            raise RuntimeError("Koloma section still visible on AASMA reports page")

        page.close()
        ctx.close()
        browser.close()
    print(f"Screenshots saved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
