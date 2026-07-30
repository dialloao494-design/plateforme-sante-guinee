#!/usr/bin/env python3
"""Capture 6 production screenshots after real UI login."""
from __future__ import annotations
import os

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/aasma-prod-proof"
OUT.mkdir(parents=True, exist_ok=True)

ACCOUNTS = {
    "01-reception-dashboard.png": ("baldoumar14@gmail.com", os.environ["AASMA_RECEPTION_PASSWORD"], "/clinical/reception"),
    "02-lab-dashboard.png": ("mamadoudianbarry06@gmail.com", os.environ["AASMA_LAB_PASSWORD"], "/clinical/lab"),
    "06-pharmacy-stock.png": ("ben752231@gmail.com", os.environ["AASMA_PHARMACY_PASSWORD"], "/clinical/pharmacy"),
}


def ui_login(page, email: str, password: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload(wait_until="networkidle")
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function(
        "() => Boolean(localStorage.getItem('token') || localStorage.getItem('access_token'))",
        timeout=120000,
    )
    page.wait_for_function(
        "() => !window.location.pathname.includes('/login')",
        timeout=120000,
    )
    page.wait_for_timeout(2000)


def assert_no_permission_banner(page) -> None:
    body = page.inner_text("body")
    for bad in ("Requires one of roles", "Accès réservé", "autre profil"):
        if bad in body:
            raise RuntimeError(f"permission banner: {bad}")


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for shot, (email, pwd, path) in ACCOUNTS.items():
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            ui_login(page, email, pwd)
            if path not in page.url:
                page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
            page.wait_for_selector("h1", timeout=120000)
            page.wait_for_timeout(4000)
            assert_no_permission_banner(page)
            page.screenshot(path=str(OUT / shot), full_page=False)
            page.close()

        page = browser.new_page(viewport={"width": 1440, "height": 900})
        ui_login(page, "mamadoudianbarry06@gmail.com", os.environ["AASMA_LAB_PASSWORD"])
        page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(4000)
        assert_no_permission_banner(page)
        page.locator("button.clinical-tab", has_text="Nouvelle demande").click()
        page.wait_for_timeout(4000)
        body = page.inner_text("body")
        if "examens" not in body or "0 examens" in body:
            page.screenshot(path=str(OUT / "FAIL-catalog.png"), full_page=True)
            raise RuntimeError("catalog count not visible in UI")
        page.screenshot(path=str(OUT / "03-lab-catalog-nouvelle-demande.png"), full_page=True)

        panel = page.locator(".lab-patient-panel")
        panel.locator('input[placeholder="Nom, téléphone ou ID"]').fill("620231409")
        panel.get_by_role("button", name="Rechercher", exact=True).click()
        page.wait_for_timeout(3000)
        prenom = panel.locator('label:has-text("Prénom")').locator("..").locator("input").first.input_value()
        if not prenom:
            raise RuntimeError("patient fields empty after phone search")
        panel.screenshot(path=str(OUT / "04-lab-patient-filled.png"))

        gly = page.locator(".lab-catalog-row", has_text="Glycémie").first
        gly.scroll_into_view_if_needed()
        gly.locator('input[type="checkbox"]').check()
        gly.locator('input[placeholder="Prix GNF"]').fill("10000")
        gly.screenshot(path=str(OUT / "05-lab-exam-price.png"))
        browser.close()

    print(f"OK — {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
