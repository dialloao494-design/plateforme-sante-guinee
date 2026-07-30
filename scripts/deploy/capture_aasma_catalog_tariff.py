#!/usr/bin/env python3
"""Capture production lab catalog screenshot with tariff prices."""
from __future__ import annotations
import os

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/aasma-prod-proof"
OUT.mkdir(parents=True, exist_ok=True)


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


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        ui_login(page, "mamadoudianbarry06@gmail.com", os.environ["AASMA_LAB_PASSWORD"])
        page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle", timeout=120000)
        page.wait_for_selector("h1", timeout=120000)
        page.wait_for_timeout(3000)
        page.get_by_role("button", name="Nouvelle demande").click()
        page.wait_for_selector("text=Catalogue AASMA", timeout=120000)
        page.wait_for_timeout(5000)
        body = page.inner_text("body")
        if "0 examens" in body:
            page.screenshot(path=str(OUT / "FAIL-catalog.png"), full_page=True)
            raise RuntimeError("catalog empty in UI")
        nfs = page.locator(".lab-catalog-row", has_text="hémogramme").first
        nfs.wait_for(timeout=120000)
        price_input = nfs.locator('input[placeholder="Prix GNF"]')
        price_value = price_input.input_value()
        if price_value != "120000":
            raise RuntimeError(f"NFS price not prefilled: {price_value!r}")
        page.screenshot(path=str(OUT / "03-lab-catalog-nouvelle-demande.png"), full_page=True)
        browser.close()
    print(f"OK — {OUT / '03-lab-catalog-nouvelle-demande.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
