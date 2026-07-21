#!/usr/bin/env python3
"""Seed AASMA production data and capture dashboard screenshots with API-loaded content."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

BASE = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
OUT = Path(__file__).resolve().parents[2] / "docs" / "ui_e2e_screenshots" / "aasma-dashboard-proof"
REPORT = Path(__file__).resolve().parents[2] / "docs" / "AASMA_DASHBOARD_PROOF.json"

ACCOUNTS = {
    "reception": ("baldoumar14@gmail.com", "AasmaRecep1!", "/clinical/reception"),
    "lab": ("mamadoudianbarry06@gmail.com", "AasmaLab1!", "/clinical/lab"),
    "pharmacy": ("ben752231@gmail.com", "AasmaPharm1!", "/clinical/pharmacy"),
}


def login(email: str, password: str) -> str:
    r = httpx.post(f"{BASE}/auth/login-json", json={"email": email, "password": password}, timeout=90)
    r.raise_for_status()
    return r.json()["access_token"]


def api_check(label: str, method: str, path: str, token: str, body=None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE}{path}"
    if method == "GET":
        r = httpx.get(url, headers=headers, timeout=90)
    else:
        r = httpx.post(url, headers=headers, json=body, timeout=90)
    return {
        "label": label,
        "path": path,
        "status": r.status_code,
        "ok": r.status_code < 400,
        "sample": r.text[:200],
    }


def seed_reception_data(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    stamp = datetime.utcnow().strftime("%H%M%S")
    patient_body = {
        "first_name": "Aissatou",
        "last_name": f"Dashboard{stamp}",
        "age": 32,
        "gender": "F",
        "phone": f"620{stamp}",
        "mother_name": "Mariama Diallo",
        "visit_destination": "Laboratoire",
        "quartier": "Ratoma",
        "profession": "Commerçante",
    }
    pr = httpx.post(f"{BASE}/clinical/reception/patients", headers=headers, json=patient_body, timeout=90)
    pr.raise_for_status()
    patient = pr.json()
    vr = httpx.post(
        f"{BASE}/clinical/workflow/visits",
        headers=headers,
        json={"patient_id": patient["id"], "workflow_type": "adult_lab"},
        timeout=90,
    )
    vr.raise_for_status()
    return {"patient": patient, "visit": vr.json()}


def seed_lab_order(lab_token: str, patient_id: int) -> dict:
    headers = {"Authorization": f"Bearer {lab_token}"}
    r = httpx.post(
        f"{BASE}/clinical/lab/walk-in-orders",
        headers=headers,
        json={
            "patient_id": patient_id,
            "payment_status": "pending",
            "tests": [{"test_code": "GLY", "test_name": "Glycémie"}],
        },
        timeout=90,
    )
    r.raise_for_status()
    return {"orders": r.json()}


def browser_shot(role: str, email: str, password: str, path: str, browser) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    try:
        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        page.reload()
        page.locator("#email").fill(email)
        page.locator("#password").fill(password)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.wait_for_load_state("networkidle", timeout=90000)
        if path not in page.url:
            page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(2500)
        text = page.inner_text("body")
        has_error = "Impossible de joindre le serveur" in text or "File laboratoire indisponible" in text
        has_mother_field = "Nom de la mère" in text
        has_catalog = "Catalogue examens" in text or "NFS" in text or "Glycémie" in text
        has_stock = "Inventaire" in text or "Paracétamol" in text or "Ordonnances" in text
        shot = OUT / f"{role}.png"
        page.screenshot(path=str(shot), full_page=True)
        return {
            "role": role,
            "url": page.url,
            "screenshot": str(shot.name),
            "has_server_error": has_error,
            "has_mother_field": has_mother_field,
            "has_lab_catalog": has_catalog,
            "has_pharmacy_content": has_stock,
            "body_snippet": text[:500],
        }
    finally:
        page.close()


def main() -> int:
    report = {"frontend": FRONTEND, "backend": BASE, "api": [], "seed": {}, "browser": []}
    recep_token = login(*ACCOUNTS["reception"][:2])
    lab_token = login(*ACCOUNTS["lab"][:2])
    pharm_token = login(*ACCOUNTS["pharmacy"][:2])

    for label, method, path, token, body in [
        ("workflow_reception", "GET", "/clinical/workflow/queue/reception", recep_token, None),
        ("workflow_lab", "GET", "/clinical/workflow/queue/lab", lab_token, None),
        ("lab_orders", "GET", "/clinical/lab/orders", lab_token, None),
        ("lab_catalog", "GET", "/clinical/lab/catalog", lab_token, None),
        ("pharmacy_inventory", "GET", "/clinical/pharmacy/inventory", pharm_token, None),
    ]:
        report["api"].append(api_check(label, method, path, token, body))

    if not all(x["ok"] for x in report["api"]):
        REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print("API checks FAILED — migration may still be pending")
        for row in report["api"]:
            print(row)
        return 1

    report["seed"] = seed_reception_data(recep_token)
    patient_id = report["seed"]["patient"]["id"]
    report["seed"]["lab_orders"] = seed_lab_order(lab_token, patient_id)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for role, (email, password, path) in ACCOUNTS.items():
            report["browser"].append(browser_shot(role, email, password, path, browser))
        browser.close()

    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    failed = [b for b in report["browser"] if b.get("has_server_error")]
    if failed:
        print("Browser still shows server errors:", failed)
        return 1
    print(f"Proof saved: {OUT} and {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
