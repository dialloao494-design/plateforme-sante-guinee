#!/usr/bin/env python3
"""Production proof: API checks + Playwright screenshots for AASMA dashboards."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "ui_e2e_screenshots" / "aasma-prod-proof"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
BASE = "https://web-production-ad6a36.up.railway.app"

ACCOUNTS = {
    "reception": ("baldoumar14@gmail.com", "AasmaRecep1!", "/clinical/reception", "01-reception-dashboard.png"),
    "lab": ("mamadoudianbarry06@gmail.com", "AasmaLab1!", "/clinical/lab", "02-lab-dashboard.png"),
    "pharmacy": ("ben752231@gmail.com", "AasmaPharm1!", "/clinical/pharmacy", "06-pharmacy-stock.png"),
}


def login(email: str, password: str) -> tuple[str, dict]:
    r = httpx.post(
        f"{BASE}/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    r.raise_for_status()
    payload = r.json()
    return payload["access_token"], payload


def api_ok(token: str, path: str, params: dict | None = None) -> tuple[int, str]:
    r = httpx.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, params=params or {}, timeout=90)
    detail = ""
    try:
        body = r.json()
        if isinstance(body, dict):
            detail = str(body.get("detail", ""))[:120]
            if path.endswith("/catalog") and r.status_code == 200:
                detail = f"categories={body.get('total_categories')} tests={body.get('total_tests')}"
        else:
            detail = str(body)[:120]
    except Exception:
        detail = r.text[:120]
    return r.status_code, detail


def capture_ui() -> None:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for role, (email, pwd, path, shot) in ACCOUNTS.items():
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
            page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            page.reload()
            page.locator("#email").fill(email)
            page.locator("#password").fill(pwd)
            page.click("button.login-submit")
            page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
            page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(3500)
            page.screenshot(path=str(OUT / shot), full_page=False)

            if role == "lab":
                page.get_by_role("button", name="Nouvelle demande", exact=True).click()
                page.wait_for_timeout(3000)
                body = page.inner_text("body")
                if "0 catégories" in body or "0 examens" in body:
                    raise SystemExit("FAIL: lab catalog still shows 0 in UI")
                page.screenshot(path=str(OUT / "03-lab-catalog-nouvelle-demande.png"), full_page=True)

                panel = page.locator(".lab-patient-panel")
                panel.locator('input[placeholder="Nom, téléphone ou ID"]').fill("Aissatou")
                panel.get_by_role("button", name="Rechercher", exact=True).click()
                page.wait_for_timeout(2500)
                if page.locator(".clinical-list button").count() > 0:
                    page.locator(".clinical-list button").first.click()
                    page.wait_for_timeout(1500)
                panel.screenshot(path=str(OUT / "04-lab-patient-filled.png"))

                gly = page.locator(".lab-catalog-row", has_text="Glycémie").first
                gly.scroll_into_view_if_needed()
                gly.locator('input[type="checkbox"]').check()
                gly.locator('input[placeholder="Prix GNF"]').fill("10000")
                gly.screenshot(path=str(OUT / "05-lab-exam-price.png"))

            page.close()
        browser.close()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"api": {}, "screenshots": str(OUT)}

    lab_token = None
    for role, (email, pwd, _, _) in ACCOUNTS.items():
        token, meta = login(email, pwd)
        if role == "lab":
            lab_token = token
        checks = {"me": api_ok(token, "/auth/me")}
        if role == "reception":
            checks["workflow"] = api_ok(token, "/clinical/workflow/queue/reception")
            checks.update(
                {
                    "queue": api_ok(token, "/clinical/reception/queue"),
                    "followups": api_ok(token, "/clinical/reception/follow-ups"),
                    "billing": api_ok(token, "/clinical/billing/charges/pending"),
                }
            )
        if role == "lab":
            checks["workflow"] = api_ok(token, "/clinical/workflow/queue/lab")
            checks.update(
                {
                    "catalog": api_ok(token, "/clinical/lab/catalog"),
                    "patient_search": api_ok(token, "/clinical/reception/patients", {"q": "Aissatou"}),
                    "phone_search": api_ok(token, "/clinical/reception/patients", {"q": "620231409"}),
                }
            )
        if role == "pharmacy":
            checks["inventory"] = api_ok(token, "/clinical/pharmacy/inventory")
        report["api"][role] = {k: {"status": s, "detail": d} for k, (s, d) in checks.items()}
        for k, (status, detail) in checks.items():
            if status >= 400:
                print(f"FAIL API {role}/{k}: {status} {detail}")
                return 1

    if lab_token:
        cat_status, cat_detail = api_ok(lab_token, "/clinical/lab/catalog")
        if "categories=0" in cat_detail or "tests=0" in cat_detail:
            print("FAIL: catalog empty on API", cat_detail)
            return 1

    capture_ui()
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK — proof saved to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
