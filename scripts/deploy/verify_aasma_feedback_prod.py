#!/usr/bin/env python3
"""Verify AASMA reception + pharmacy production feedback fixes."""
import os
import json
import re
import sys
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

FRONTEND = "https://plateforme-sante-guinee.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
PHARM_EMAIL, PHARM_PWD = "ben752231@gmail.com", os.environ["AASMA_PHARMACY_PASSWORD"]
RECEP_EMAIL, RECEP_PWD = "baldoumar14@gmail.com", os.environ["AASMA_RECEPTION_PASSWORD"]
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
        "specialty_picker": "Consultation spécialisée" in js,
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
        inv = httpx.get(f"{BACKEND}/clinical/pharmacy/inventory", headers=h, timeout=60)
        out["inventory"] = inv.status_code
        out["inventory_count"] = len(inv.json()) if inv.status_code == 200 else 0
    if recep:
        h = {"Authorization": f"Bearer {recep}"}
        cat = httpx.get(f"{BACKEND}/clinical/reception/his/billing-catalog", headers=h, timeout=60)
        out["billing_catalog"] = cat.status_code
        out["specialties_count"] = len((cat.json() or {}).get("specialized_specialties") or []) if cat.status_code == 200 else 0
    return out


def pdf_checks():
    recep = login(RECEP_EMAIL, RECEP_PWD)
    if not recep:
        return {"pdf_ok": False}
    h = {"Authorization": f"Bearer {recep}"}
    invs = httpx.get(f"{BACKEND}/clinical/reception/his/invoices", headers=h, timeout=60)
    if invs.status_code != 200 or not invs.json():
        return {"pdf_ok": False, "reason": "no invoices"}
    inv_id = invs.json()[0]["id"]
    pdf = httpx.get(f"{BACKEND}/clinical/reception/his/invoices/{inv_id}/receipt", headers=h, timeout=60)
    text = pdf.content.decode("latin-1", errors="replace") if pdf.status_code == 200 else ""
    return {
        "receipt_pdf": pdf.status_code,
        "has_clinic_name": "CHFM" in text and "AASMA" in text,
        "has_payment_summary": "Montant total" in text and "Reste" in text,
        "has_footer": "Imprim" in text and "Page 1 sur 1" in text,
    }


def ui_checks():
    checks = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        # Reception
        page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
        page.locator("#email").fill(RECEP_EMAIL)
        page.locator("#password").fill(RECEP_PWD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/clinical/reception", wait_until="networkidle", timeout=120000)
        page.locator(".reception-his-tabs button", has_text="Facturation").click()
        page.wait_for_timeout(1000)
        body = page.locator("body").inner_text()
        checks["reception_specialty"] = "Consultation spécialisée" in body
        checks["reception_specialty_dropdown"] = page.locator(".reception-his-specialty-picker select").count() > 0

        # Select patient and open invoice for split payment UI
        page.locator(".reception-his-search-inline input").fill("620")
        page.wait_for_timeout(3000)
        if page.locator(".reception-his-search-results button").count() > 0:
            page.locator(".reception-his-search-results button").first.click(force=True)
            page.wait_for_timeout(1500)
        invoices = page.locator("table.reception-his-invoices tbody tr")
        if invoices.count() > 0:
            invoices.first.click()
            page.wait_for_timeout(1000)
        billing_body = page.locator("body").inner_text()
        checks["reception_split_payment"] = "Ligne de paiement" in billing_body or "Mode de paiement" in billing_body
        page.screenshot(path=str(OUT / "01-reception-billing.png"), full_page=True)

        browser.close()

        # Pharmacy — fresh browser (no session bleed)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
        page.locator("#email").fill(PHARM_EMAIL)
        page.locator("#password").fill(PHARM_PWD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/clinical/pharmacy", wait_until="networkidle", timeout=120000)
        page.locator("#pharmacy-patient-search").fill("620")
        page.wait_for_timeout(4000)
        results = page.locator(".reception-his-search-results--inline button")
        checks["pharmacy_auto_search"] = results.count() > 0
        page.screenshot(path=str(OUT / "02-pharmacy-search.png"), full_page=True)
        if results.count() > 0:
            results.first.scroll_into_view_if_needed()
            results.first.click(force=True)
            page.wait_for_timeout(2000)
        pbody = page.locator("body").inner_text()
        checks["pharmacy_patient_fields"] = "Informations patient" in pbody and (
            "Patient actif" in pbody or "Patient sélectionné" in pbody or "N° dossier" in pbody
        )
        page.screenshot(path=str(OUT / "03-pharmacy-patient.png"), full_page=True)

        page.locator("button.pharmacy-tab", has_text="Stock").click()
        page.wait_for_timeout(1500)
        checks["pharmacy_stock"] = "Stock pharmacie" in page.locator("body").inner_text()
        page.screenshot(path=str(OUT / "04-pharmacy-stock.png"), full_page=True)
        browser.close()
    return checks


def main():
    report = {
        "bundle": bundle_checks(),
        "api": api_checks(),
        "pdf": pdf_checks(),
        "ui": ui_checks(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    ok = (
        report["bundle"].get("split_payment_ui")
        and report["api"].get("specialties_count", 0) >= 9
        and report["api"].get("pharmacy_hits", 0) > 0
        and report["ui"].get("pharmacy_auto_search")
        and report["ui"].get("pharmacy_stock")
        and report["pdf"].get("has_clinic_name")
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
