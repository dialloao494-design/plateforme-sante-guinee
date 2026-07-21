#!/usr/bin/env python3
"""Capture production catalog screenshots proving tariff sheet match."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/aasma-tariff-proof"
OUT.mkdir(parents=True, exist_ok=True)

# Spot-checks from each of the 4 tariff photos
SPOTS = [
    ("01-sheet1-ac-anti-hbc.png", "Ac anti HBc Total", "300000"),
    ("02-sheet2-ddimeres.png", "D-Dimères", "300000"),
    ("03-sheet3-nfs.png", "NFS (hemogramme complet)", "120000"),
    ("04-sheet4-tsh.png", "TSH", "300000"),
    ("05-sheet2-hpylori.png", "H.Pylori dans le sang", "250000"),
    ("06-sheet1-ca125.png", "CA 125", "350000"),
]


def ui_login(page) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload(wait_until="networkidle")
    page.locator("#email").fill("mamadoudianbarry06@gmail.com")
    page.locator("#password").fill("AasmaLab1!")
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


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        ui_login(page)
        if "/clinical/lab" not in page.url:
            page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle", timeout=120000)
        page.wait_for_selector("h1", timeout=120000)
        page.get_by_role("button", name="Nouvelle demande").click()
        page.wait_for_selector("text=Catalogue AASMA", timeout=120000)
        page.wait_for_timeout(4000)

        body = page.inner_text("body")
        if "0 examens" in body:
            raise RuntimeError("catalog empty")

        page.screenshot(path=str(OUT / "00-catalog-full-top.png"), full_page=False)

        for filename, label, expected_price in SPOTS:
            row = page.locator(".lab-catalog-row", has_text=label).first
            row.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            price = row.locator('input[placeholder="Prix GNF"]').input_value()
            if price != expected_price:
                raise RuntimeError(f"{label}: expected {expected_price}, got {price!r}")
            row.screenshot(path=str(OUT / filename))

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "07-catalog-full-bottom.png"), full_page=False)

        browser.close()

    print(f"OK — {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
