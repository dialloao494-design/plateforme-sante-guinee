#!/usr/bin/env python3
"""Post-deploy production verification — pharmacy, workflows, RBAC, security."""

from __future__ import annotations

import json
import re
import sys
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
OUT = Path(__file__).resolve().parents[2] / "docs" / "PRODUCTION_VERIFY_REPORT.json"

ACCOUNTS = {
    "reception": ("reception.demo@sante-gn.test", "ReceptionDemo1!"),
    "doctor": ("doctor.demo@sante-gn.test", "DoctorDemo1!"),
    "lab": ("lab.demo@sante-gn.test", "LabDemo1!"),
    "pharmacy": ("pharmacy.demo@sante-gn.test", "PharmaDemo1!"),
    "cashier": ("reception.demo@sante-gn.test", "ReceptionDemo1!"),
    "clinic_admin": ("clinic.admin.a@sante-gn.test", "ClinicAdminA1!"),
}

results: list[dict] = []


def log(area: str, name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    results.append({"area": area, "check": name, "status": status, "detail": detail})
    msg = f"[{status}] {area} — {name}"
    if detail:
        msg += f" ({detail})"
    print(msg)


def login(email: str, password: str) -> str | None:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        return None
    return r.json().get("access_token")


def api(method: str, path: str, token: str, **kwargs) -> httpx.Response:
    return httpx.request(
        method,
        f"{BACKEND}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
        **kwargs,
    )


def wait_frontend_new_build(max_wait_s: int = 360) -> bool:
    marker = "Poste pharmacie"
    deadline = time.time() + max_wait_s
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            index = httpx.get(FRONTEND, timeout=30).text
            assets = re.findall(r"/assets/[^\"']+\.js", index)
            for asset in assets[:5]:
                js = httpx.get(f"{FRONTEND}{asset}", timeout=60).text
                if marker in js or "pharmacy-tabs" in js:
                    log("Deploy", "Frontend new pharmacy bundle", True, asset)
                    return True
            log("Deploy", "Frontend bundle poll", False, f"attempt {attempt} — old build")
        except Exception as exc:
            log("Deploy", "Frontend bundle poll", False, str(exc)[:120])
        time.sleep(20)
    return False


def wait_backend_pharmacy_api(max_wait_s: int = 360) -> bool:
    tok = login(*ACCOUNTS["pharmacy"])
    if not tok:
        log("Deploy", "Backend pharmacy login", False)
        return False
    deadline = time.time() + max_wait_s
    while time.time() < deadline:
        r = api("GET", "/clinical/pharmacy/orders", tok, params={"scope": "all"})
        if r.status_code == 200:
            data = r.json()
            if data and "doctor_name" in data[0]:
                log("Deploy", "Backend enriched pharmacy API", True)
                return True
        time.sleep(15)
    log("Deploy", "Backend enriched pharmacy API", False, r.text[:120] if r else "")
    return False


def verify_pharmacy_api(tok: str) -> None:
    inv_before = api("GET", "/clinical/pharmacy/inventory", tok).json()
    sku = f"E2E-{uuid.uuid4().hex[:6].upper()}"
    test_item = {
        "sku": sku,
        "medication_name": f"Test Med {sku}",
        "quantity": 5,
        "reorder_level": 10,
        "unit_price_gnf": 15000,
        "batch_number": "LOT-TEST",
        "expiry_date": (date.today() + timedelta(days=20)).isoformat(),
        "supplier": "QA Supplier",
    }
    r = api("POST", "/clinical/pharmacy/inventory", tok, json=test_item)
    log("Pharmacy", "Stock upsert API", r.status_code in (200, 201), f"status={r.status_code}")

    inv_after = api("GET", "/clinical/pharmacy/inventory", tok).json()
    item = next((i for i in inv_after if i.get("sku") == sku), None)
    log("Pharmacy", "Low-stock alert data", bool(item and item.get("low_stock")), f"qty={item and item.get('quantity')}")

    orders = api("GET", "/clinical/pharmacy/orders", tok, params={"scope": "all"}).json()
    log("Pharmacy", "Orders scope=all", isinstance(orders, list), f"count={len(orders)}")
    if orders:
        sample = orders[0]
        log("Pharmacy", "Order has doctor_name field", "doctor_name" in sample)
        log("Pharmacy", "Order has items field", "items" in sample)


def verify_rbac() -> None:
    rec = login(*ACCOUNTS["reception"])
    lab = login(*ACCOUNTS["lab"])
    pharma = login(*ACCOUNTS["pharmacy"])
    admin = login(*ACCOUNTS["clinic_admin"])

    for path in ("/clinical/lab/orders", "/clinical/pharmacy/orders", "/clinical/admin/backup-status"):
        r = api("GET", path, rec)
        log("RBAC", f"Reception denied {path}", r.status_code == 403, str(r.status_code))

    for path in ("/clinical/pharmacy/orders", "/clinical/reception/queue", "/clinical/admin/backup-status"):
        r = api("GET", path, lab)
        log("RBAC", f"Lab denied {path}", r.status_code == 403, str(r.status_code))

    for path in ("/clinical/reception/queue", "/clinical/lab/orders", "/clinical/admin/backup-status"):
        r = api("GET", path, pharma)
        log("RBAC", f"Pharmacy denied {path}", r.status_code == 403, str(r.status_code))

    r = api("POST", "/clinical/clinics", admin, json={"name": "Forbidden", "city": "Conakry"})
    log("RBAC", "Clinic admin cannot create clinic", r.status_code == 403, str(r.status_code))


def verify_core_modules() -> None:
    checks = [
        ("reception", "GET", "/clinical/reception/queue"),
        ("doctor", "GET", "/clinical/doctor/queue"),
        ("lab", "GET", "/clinical/lab/orders"),
        ("pharmacy", "GET", "/clinical/pharmacy/orders"),
        ("reception", "GET", "/clinical/billing/charges/pending"),
        ("reception", "GET", "/clinical/immunization/schedule"),
        ("clinic_admin", "GET", "/clinical/hospitalization/admissions"),
        ("reception", "GET", "/clinical/discharge/visits/open"),
    ]
    for role, method, path in checks:
        tok = login(*ACCOUNTS[role])
        if not tok:
            log("Core", f"{role} login", False)
            continue
        r = api(method, path, tok)
        log("Core", f"{role} {path}", r.status_code in (200, 404), str(r.status_code))


def verify_security() -> None:
    html = httpx.get(f"{FRONTEND}/login", timeout=30).text.lower()
    log("Security", "Login page has no prefilled demo passwords", "receptiondemo1!" not in html)
    r = httpx.get(f"{BACKEND}/clinical/pharmacy/orders", timeout=30)
    log("Security", "Pharmacy API requires auth", r.status_code in (401, 403), str(r.status_code))


def run_playwright_pharmacy() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("Pharmacy UI", "Playwright available", False, "install playwright")
        return

    shot_dir = Path(__file__).resolve().parents[2] / "docs" / "ui_e2e_screenshots" / "prod-pharmacy-verify"
    shot_dir.mkdir(parents=True, exist_ok=True)

    email, pwd = ACCOUNTS["pharmacy"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        page.reload()
        page.fill("#email", email)
        page.fill("#password", pwd)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=90000)
        page.goto(f"{FRONTEND}/clinical/pharmacy", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        body = page.content()
        log("Pharmacy UI", "Dashboard title Poste pharmacie", "Poste pharmacie" in body)
        log("Pharmacy UI", "KPI cards visible", page.locator(".pharmacy-stat-grid").count() > 0)
        for tab in ("Ordonnances", "Stock", "Alertes", "Mouvements"):
            log("Pharmacy UI", f"Tab {tab}", page.locator(f"button.pharmacy-tab:has-text('{tab}')").count() > 0)

        page.screenshot(path=str(shot_dir / "01_pharmacy_dashboard.png"), full_page=True)

        page.locator("button.pharmacy-tab:has-text('Stock')").click()
        page.wait_for_timeout(1000)
        page.screenshot(path=str(shot_dir / "02_pharmacy_stock.png"), full_page=True)

        page.locator("button.pharmacy-tab:has-text('Alertes')").click()
        page.wait_for_timeout(1000)
        page.screenshot(path=str(shot_dir / "03_pharmacy_alerts.png"), full_page=True)

        page.locator("button.pharmacy-tab:has-text('Ordonnances')").click()
        prepare = page.locator("button:has-text('Préparer')").first
        if prepare.count():
            prepare.click()
            page.wait_for_timeout(1500)
        dispense = page.locator("button:has-text('Délivrer')").first
        if dispense.count():
            dispense.click()
            page.wait_for_timeout(2000)
            log("Pharmacy UI", "Dispense action", page.locator(".clinical-success").count() > 0)
        else:
            log("Pharmacy UI", "Dispense action", True, "no pending order")

        page.locator("button.pharmacy-tab:has-text('Mouvements')").click()
        page.wait_for_timeout(1000)
        page.screenshot(path=str(shot_dir / "04_pharmacy_movements.png"), full_page=True)
        log("Pharmacy UI", "Movements tab renders", page.locator(".pharmacy-table").count() > 0)

        browser.close()
        print(f"Screenshots: {shot_dir}")


def main() -> int:
    print(f"Backend:  {BACKEND}")
    print(f"Frontend: {FRONTEND}\n")

    wait_backend_pharmacy_api()
    wait_frontend_new_build()

    tok = login(*ACCOUNTS["pharmacy"])
    log("Pharmacy", "Pharmacy login", bool(tok))
    if tok:
        verify_pharmacy_api(tok)

    verify_core_modules()
    verify_rbac()
    verify_security()
    run_playwright_pharmacy()

    fails = sum(1 for r in results if r["status"] == "FAIL")
    report = {
        "backend": BACKEND,
        "frontend": FRONTEND,
        "commit": "a07cd30",
        "results": results,
        "summary": {"total": len(results), "failures": fails},
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport: {OUT}")
    print(f"TOTAL: {len(results)} | FAILURES: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
