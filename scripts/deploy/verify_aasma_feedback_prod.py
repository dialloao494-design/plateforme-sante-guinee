#!/usr/bin/env python3
"""Verify AASMA reception + pharmacy production feedback fixes."""
import json
import re
import sys
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
PHARM_EMAIL, PHARM_PWD = "ben752231@gmail.com", "AasmaPharm1!"
RECEP_EMAIL, RECEP_PWD = "baldoumar14@gmail.com", "AasmaRecep1!"
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/aasma-feedback-proof"
OUT.mkdir(parents=True, exist_ok=True)


def login(email, pwd):
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": email, "password": pwd}, timeout=60)
    return r.json()["access_token"] if r.status_code == 200 else None


def bundle_checks():
    html = httpx.get(f"{FRONTEND}/clinical/pharmacy", timeout=60).text
    m = re.search(r"clinical-pages-[^\"]+\.js", html)
    js = httpx.get(f"{FRONTEND}/assets/{m.group(0)}", timeout=120).text if m else ""
    return {
        "split_payment_ui": "Ligne de paiement" in js and "Enregistrer le(s) paiement(s)" in js,
        "specialty_picker": "Consultation spécialisée — spécialité" in js or "specialized_specialties" in js,
        "pharmacy_pdf_print": "Imprimer PDF (AASMA)" in js,
    }


def api_checks():
    pharm = login(PHARM_EMAIL, PHARM_PWD)
    recep = login(RECEP_EMAIL, RECEP_PWD)
    out = {}
    if pharm:
        h = {"Authorization": f"Bearer {pharm}"}
        r = httpx.get(f"{BACKEND}/clinical/pharmacy/patients/search", params={"q": "620"}, headers=h, timeout=60)
        out["pharmacy_search"] = r.status_code
        out["pharmacy_hits"] = len(r.json()) if r.status_code == 200 else 0
    if recep:
        h = {"Authorization": f"Bearer {recep}"}
        cat = httpx.get(f"{BACKEND}/clinical/reception/his/billing-catalog", headers=h, timeout=60)
        out["billing_catalog"] = cat.status_code
        out["specialties_count"] = len((cat.json() or {}).get("specialized_specialties") or []) if cat.status_code == 200 else 0
    return out


def ui_checks():
    checks = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
        page.locator("#email").fill(RECEP_EMAIL)
        page.locator("#password").fill(RECEP_PWD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/clinical/reception", wait_until="networkidle", timeout=120000)
        page.locator("button.reception-his-tab", has_text="Facturation").click()
        page.wait_for_timeout(1500)
        body = page.locator("body").inner_text()
        checks["reception_split_payment"] = "Ligne de paiement" in body
        checks["reception_specialty"] = "Consultation spécialisée — spécialité" in body
        page.screenshot(path=str(OUT / "01-reception-billing.png"), full_page=True)

        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
        page.locator("#email").fill(PHARM_EMAIL)
        page.locator("#password").fill(PHARM_PWD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/clinical/pharmacy", wait_until="networkidle", timeout=120000)
        page.locator("#pharmacy-patient-search").fill("620")
        page.wait_for_timeout(2500)
        checks["pharmacy_auto_search"] = page.locator(".reception-his-search-results button").count() > 0
        page.screenshot(path=str(OUT / "02-pharmacy-search.png"), full_page=True)
        page.locator(".reception-his-search-results button").first.click()
        page.wait_for_timeout(1500)
        pbody = page.locator("body").inner_text()
        checks["pharmacy_patient_fields"] = "Informations patient" in pbody and "N° dossier" in pbody
        page.screenshot(path=str(OUT / "03-pharmacy-patient.png"), full_page=True)
        page.locator("button.pharmacy-tab", has_text="Stock").click()
        page.wait_for_timeout(1000)
        checks["pharmacy_stock"] = "Stock pharmacie" in page.locator("body").inner_text()
        page.screenshot(path=str(OUT / "04-pharmacy-stock.png"), full_page=True)
        browser.close()
    return checks


def main():
    report = {"bundle": bundle_checks(), "api": api_checks(), "ui": ui_checks()}
    print(json.dumps(report, indent=2, ensure_ascii=False))
    ok = (
        report["bundle"].get("split_payment_ui")
        and report["api"].get("specialties_count", 0) >= 9
        and report["ui"].get("reception_split_payment")
        and report["ui"].get("pharmacy_auto_search")
        and report["ui"].get("pharmacy_stock")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
