#!/usr/bin/env python3
"""Production stability proof — 4 roles + lab patient panel."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
FRONTEND = "https://frontend-seven-rust-94.vercel.app"
OUT = Path(__file__).resolve().parents[2] / "docs/ui_e2e_screenshots/stability-proof"
OUT.mkdir(parents=True, exist_ok=True)

ACCOUNTS = [
    ("01-admin.png", "contactpolycliniqueaasma@gmail.com", "AasmaAdmin1!", "/clinical/admin"),
    ("02-reception.png", "baldoumar14@gmail.com", "AasmaRecep1!", "/clinical/reception"),
    ("03-laboratory.png", "mamadoudianbarry06@gmail.com", "AasmaLab1!", "/clinical/lab"),
    ("04-pharmacy.png", "ben752231@gmail.com", "AasmaPharm1!", "/clinical/pharmacy"),
]


def assert_clean(page) -> None:
    body = page.inner_text("body")
    for bad in ("Requires one of roles", "Accès réservé", "autre profil"):
        if bad in body:
            raise RuntimeError(f"permission banner: {bad}")


def login_tab(context, email: str, password: str, path: str):
    page = context.new_page(viewport={"width": 1280, "height": 900})
    page.goto(f"{FRONTEND}/login", wait_until="networkidle", timeout=120000)
    page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    page.reload(wait_until="networkidle")
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function(
        "() => Boolean(sessionStorage.getItem('token') || sessionStorage.getItem('access_token'))",
        timeout=120000,
    )
    page.wait_for_function(
        "() => !window.location.pathname.includes('/login')",
        timeout=120000,
    )
    if path not in page.url:
        page.goto(f"{FRONTEND}{path}", wait_until="networkidle", timeout=120000)
    page.wait_for_selector("h1", timeout=120000)
    page.wait_for_timeout(3000)
    assert_clean(page)
    return page


def main() -> int:
    results = {"tabs": [], "patient_search": None, "h_pylori": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        pages = []
        for shot, email, pwd, path in ACCOUNTS:
            page = login_tab(context, email, pwd, path)
            page.screenshot(path=str(OUT / shot), full_page=False)
            results["tabs"].append({"screenshot": shot, "url": page.url, "ok": True})
            pages.append(page)

        lab = pages[2]
        for p in pages[:2] + pages[3:]:
            assert_clean(p)

        lab.get_by_role("button", name="Nouvelle demande").click()
        lab.wait_for_timeout(2000)
        panel = lab.locator(".lab-patient-panel")
        panel.locator('input[placeholder="Nom, téléphone ou ID"]').fill("620231409")
        panel.get_by_role("button", name="Rechercher", exact=True).click()
        lab.wait_for_timeout(3000)
        prenom = panel.locator('input[placeholder="Prénom"]').input_value()
        nom = panel.locator('input[placeholder="Nom de famille"]').input_value()
        phone = panel.locator('input[placeholder="Numéro de téléphone"]').input_value()
        results["patient_search"] = {"prenom": prenom, "nom": nom, "phone": phone}
        if not prenom or not nom:
            raise RuntimeError("patient fields not populated")
        panel.screenshot(path=str(OUT / "05-lab-patient-filled.png"))

        body = lab.inner_text("body")
        for label in ("H.Pylori dans le sang", "H.Pylori dans les selles", "H. Pylori dans le sang"):
            if label in body:
                results["h_pylori"].append(label)
        lab.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        lab.wait_for_timeout(1000)
        for label in ("H. Pylori dans les selles",):
            if label in lab.inner_text("body"):
                results["h_pylori"].append(label)
        lab.screenshot(path=str(OUT / "06-lab-catalog-hpylori.png"), full_page=False)

        for p in pages:
            assert_clean(p)

        browser.close()

    report = OUT.parent.parent / "STABILITY_PROOF.json"
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"OK — {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
