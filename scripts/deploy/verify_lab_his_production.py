#!/usr/bin/env python3
"""Production verification for Laboratory HIS dashboard."""
from __future__ import annotations
import os


import json
import sys
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

FRONTEND = "https://plateforme-sante-guinee.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
EMAIL = "mamadoudianbarry06@gmail.com"
PASSWORD = os.environ["AASMA_LAB_PASSWORD"]
OUT = Path(__file__).resolve().parents[2] / "docs" / "LAB_HIS_PRODUCTION_PROOF.json"


def main() -> int:
    results: list[dict] = []
    with httpx.Client(timeout=90) as client:
        login = client.post(f"{BACKEND}/auth/login-json", json={"email": EMAIL, "password": PASSWORD})
        results.append({"check": "login", "pass": login.status_code == 200})
        if login.status_code != 200:
            OUT.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
            return 1
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for path in ["/clinical/lab/catalog", "/clinical/lab/patients/search?q=PAT"]:
            r = client.get(f"{BACKEND}{path}", headers=headers)
            results.append({"check": path, "pass": r.status_code == 200, "status": r.status_code})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
        page.locator("#email").fill(EMAIL)
        page.locator("#password").fill(PASSWORD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/clinical/lab", wait_until="networkidle", timeout=120000)
        body = page.locator("body").inner_text()
        ui_checks = [
            ("lab_dashboard_title", "Tableau de bord — Laboratoire" in body),
            ("workflow_tab", "Tableau de bord Labo" in body),
            ("catalog_tab", "Catalogue tarifaire" in body),
            ("patient_search", "Recherche patient" in body),
            ("paper_section", "Examens biologiques" in body),
        ]
        page.click("button:has-text('Catalogue tarifaire')")
        page.wait_for_timeout(500)
        catalog_body = page.locator("body").inner_text()
        ui_checks.append(("catalog_table", "Catalogue tarifaire laboratoire" in catalog_body))
        ui_checks.append(("catalog_search", "Rechercher une analyse" in catalog_body))
        for name, ok in ui_checks:
            results.append({"check": name, "pass": ok})
        page.screenshot(path=str(OUT.with_suffix(".png")), full_page=True)
        browser.close()

    OUT.write_text(json.dumps({"frontend": FRONTEND, "results": results}, indent=2), encoding="utf-8")
    failed = [r for r in results if not r["pass"]]
    for r in results:
        print(f"{'PASS' if r['pass'] else 'FAIL'} {r['check']}")
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
