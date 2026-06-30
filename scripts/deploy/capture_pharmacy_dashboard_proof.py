#!/usr/bin/env python3
"""Production verification for pharmacy module corrections."""
import json
import re
import sys
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
EMAIL = "ben752231@gmail.com"
PASSWORD = "AasmaPharm1!"
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/pharmacy-dashboard-proof"
OUT.mkdir(parents=True, exist_ok=True)


def check_bundle():
    html = httpx.get(f"{FRONTEND}/clinical/pharmacy", timeout=60).text
    m = re.search(r"clinical-pages-[^\"]+\.js", html)
    b = m.group(0) if m else None
    js = httpx.get(f"{FRONTEND}/assets/{b}", timeout=120).text if b else ""
    return {
        "bundle": b,
        "has_stock_tab": "Stock" in js and "PharmacyStockTab" in js or "Stock pharmacie" in js,
        "no_search_button": "Rechercher" not in js or "pharmacy-his-search-btn" not in js,
        "split_payment": "addPharmacyChargePayment" in js or "Enregistrer le paiement" in js,
    }


def check_api(token):
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=60, headers=headers) as c:
        inv = c.get(f"{BACKEND}/clinical/pharmacy/inventory")
        search = c.get(f"{BACKEND}/clinical/pharmacy/inventory/search", params={"q": "Para"})
        return {
            "inventory": inv.status_code,
            "inventory_search": search.status_code,
            "search_hits": len(search.json()) if search.status_code == 200 else 0,
        }


def capture_ui():
    checks = {}
    with sync_playwright() as p:
        page = p.chromium.launch(headless=True).new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
        page.locator("#email").fill(EMAIL)
        page.locator("#password").fill(PASSWORD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/clinical/pharmacy", wait_until="networkidle", timeout=120000)
        body = page.locator("body").inner_text()
        checks["has_dispensation_tab"] = "Dispensation" in body
        checks["has_stock_tab"] = "Stock" in body
        page.screenshot(path=str(OUT / "01-pharmacy-tabs.png"), full_page=True)
        page.locator("button.pharmacy-tab", has_text="Stock").click()
        page.wait_for_timeout(1500)
        stock_body = page.locator("body").inner_text()
        checks["stock_module"] = "Stock pharmacie" in stock_body
        page.screenshot(path=str(OUT / "02-pharmacy-stock.png"), full_page=True)
        page.locator("button.pharmacy-tab", has_text="Dispensation").click()
        page.wait_for_timeout(500)
        page.locator("#pharmacy-patient-search").fill("620")
        page.wait_for_timeout(2000)
        checks["auto_patient_search"] = page.locator(".reception-his-search-results button").count() > 0
        checks["no_search_button"] = page.locator("button.pharmacy-his-search-btn").count() == 0
        page.screenshot(path=str(OUT / "03-pharmacy-patient-search.png"), full_page=True)
        page.close()
    return checks


def main():
    login = httpx.post(f"{BACKEND}/auth/login-json", json={"email": EMAIL, "password": PASSWORD}, timeout=60)
    token = login.json().get("access_token") if login.status_code == 200 else None
    report = {
        "bundle": check_bundle(),
        "api": check_api(token) if token else {"login": login.status_code},
        "ui": capture_ui(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    ok = (
        report["ui"].get("has_stock_tab")
        and report["ui"].get("stock_module")
        and report["ui"].get("auto_patient_search")
        and report["ui"].get("no_search_button")
        and report["api"].get("inventory_search") == 200
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
