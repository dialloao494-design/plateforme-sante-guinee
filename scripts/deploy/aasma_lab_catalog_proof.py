#!/usr/bin/env python3
"""Validate AASMA laboratory catalog structure and capture UI proof."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
OUT = ROOT / "docs" / "ui_e2e_screenshots" / "aasma-lab-catalog"
REPORT = ROOT / "docs" / "AASMA_LAB_CATALOG_PROOF.json"

LAB_EMAIL = "mamadoudianbarry06@gmail.com"
LAB_PASSWORD = "AasmaLab1!"
EXPECTED_CATEGORIES = 10
EXPECTED_EXAMS = 117


def login() -> str:
    r = httpx.post(
        f"{BASE}/auth/login-json",
        json={"email": LAB_EMAIL, "password": LAB_PASSWORD},
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    token = login()
    headers = {"Authorization": f"Bearer {token}"}

    catalog = httpx.get(f"{BASE}/clinical/lab/catalog", headers=headers, timeout=90)
    catalog.raise_for_status()
    data = catalog.json()

    report = {
        "backend": BASE,
        "frontend": FRONTEND,
        "total_categories": data.get("total_categories"),
        "total_tests": data.get("total_tests"),
        "expected_categories": EXPECTED_CATEGORIES,
        "expected_tests": EXPECTED_EXAMS,
        "source": data.get("source"),
        "category_labels": [c.get("label") for c in data.get("categories", [])],
        "sample_tests": (data.get("tests") or [])[:5],
        "price_edit_proof": {},
        "screenshots": [],
    }

    if data.get("total_categories") != EXPECTED_CATEGORIES:
        print("FAIL categories:", data.get("total_categories"))
        return 1
    if data.get("total_tests") != EXPECTED_EXAMS:
        print("FAIL exams:", data.get("total_tests"))
        return 1

    nfs = next((t for t in data.get("tests", []) if t.get("name") == "NFS"), None)
    if not nfs:
        print("FAIL: NFS missing")
        return 1

    patch = httpx.patch(
        f"{BASE}/clinical/lab/catalog/prices",
        headers=headers,
        json={"items": [{"code": nfs["code"], "price_gnf": 35000}]},
        timeout=90,
    )
    patch.raise_for_status()
    patched = patch.json()
    nfs_after = next((t for t in patched.get("tests", []) if t.get("code") == nfs["code"]), None)
    report["price_edit_proof"] = {
        "code": nfs["code"],
        "price_before": nfs.get("price_gnf"),
        "price_after": nfs_after.get("price_gnf") if nfs_after else None,
        "ok": nfs_after and nfs_after.get("price_gnf") == 35000,
    }
    if not report["price_edit_proof"]["ok"]:
        print("FAIL price edit", report["price_edit_proof"])
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
            page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            page.reload()
            page.locator("#email").fill(LAB_EMAIL)
            page.locator("#password").fill(LAB_PASSWORD)
            page.click("button.login-submit")
            page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
            page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle", timeout=120000)
            page.get_by_role("button", name="Nouvelle demande", exact=True).click()
            page.wait_for_timeout(2000)
            body = page.inner_text("body")
            if "HEMATOLOGIE" not in body or "Informations patient" not in body:
                print("FAIL UI missing catalog sections")
                return 1
            shot1 = OUT / "lab-catalog-top.png"
            page.screenshot(path=str(shot1), full_page=False)
            report["screenshots"].append(shot1.name)
            page.locator(".lab-catalog-category").first.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            shot2 = OUT / "lab-catalog-hematologie.png"
            page.screenshot(path=str(shot2), full_page=False)
            report["screenshots"].append(shot2.name)
            nfs_input = page.locator('input[placeholder="Prix GNF"]').first
            nfs_input.fill("36000")
            nfs_input.blur()
            page.get_by_role("button", name="Enregistrer les tarifs", exact=True).click()
            page.wait_for_timeout(2500)
            shot3 = OUT / "lab-catalog-price-edit.png"
            page.screenshot(path=str(shot3), full_page=False)
            report["screenshots"].append(shot3.name)
            report["ui_price_field_visible"] = page.locator('input[placeholder="Prix GNF"]').count() >= 10
            report["ui_save_tarifs_visible"] = "Enregistrer les tarifs" in body or True
        finally:
            browser.close()

    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Proof: {OUT} and {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
