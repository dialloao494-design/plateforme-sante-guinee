#!/usr/bin/env python3
"""Reset and verify all real AASMA staff logins on production."""
from __future__ import annotations

import os

import sys
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

BASE = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
AASMA_ID = 17
ADMIN_EMAIL = "platform.admin@sante-gn.test"
ADMIN_PASSWORD = "PlatformAdmin1!"
OUT = Path(__file__).resolve().parents[2] / "docs" / "ui_e2e_screenshots" / "aasma-login-proof"

# Fixed passwords — uppercase + digit + 8+ chars
REAL_STAFF = [
    {
        "role": "Admin clinique",
        "email": "contactpolycliniqueaasma@gmail.com",
        "password": os.environ["AASMA_ADMIN_PASSWORD"],
        "dashboard": "/clinical/admin",
        "staff_id": None,
    },
    {
        "role": "Réception",
        "email": "baldoumar14@gmail.com",
        "password": os.environ["AASMA_RECEPTION_PASSWORD"],
        "dashboard": "/clinical/reception",
        "staff_id": None,
    },
    {
        "role": "Laboratoire",
        "email": "mamadoudianbarry06@gmail.com",
        "password": os.environ["AASMA_LAB_PASSWORD"],
        "dashboard": "/clinical/lab",
        "staff_id": None,
    },
    {
        "role": "Pharmacie",
        "email": "ben752231@gmail.com",
        "password": os.environ["AASMA_PHARMACY_PASSWORD"],
        "dashboard": "/clinical/pharmacy",
        "staff_id": None,
    },
]


def login_admin() -> str:
    r = httpx.post(
        f"{BASE}/auth/login-json",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def reset_passwords(token: str) -> list[tuple[str, str, bool, str]]:
    headers = {"Authorization": f"Bearer {token}"}
    staff = httpx.get(f"{BASE}/platform/clinics/{AASMA_ID}/staff", headers=headers, timeout=60).json()
    by_email = {s["email"].lower(): s for s in staff}
    results = []
    for acc in REAL_STAFF:
        member = by_email.get(acc["email"].lower())
        if not member:
            results.append((acc["role"], acc["email"], False, "account not found"))
            continue
        acc["staff_id"] = member["id"]
        r = httpx.post(
            f"{BASE}/platform/clinics/{AASMA_ID}/staff/{member['id']}/reset-password",
            headers=headers,
            json={"new_password": acc["password"]},
            timeout=60,
        )
        ok = r.status_code == 200
        results.append((acc["role"], acc["email"], ok, acc["password"] if ok else r.text[:80]))
    return results


def api_login(email: str, password: str) -> tuple[bool, str]:
    r = httpx.post(f"{BASE}/auth/login-json", json={"email": email, "password": password}, timeout=60)
    if r.status_code != 200:
        return False, r.text[:100]
    return True, "OK"


def browser_proof() -> list[tuple[str, bool, str, str]]:
    OUT.mkdir(parents=True, exist_ok=True)
    proofs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for acc in REAL_STAFF:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            slug = acc["email"].split("@")[0].replace(".", "-")[:30]
            try:
                page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
                page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
                page.reload()
                page.locator("#email").fill(acc["email"])
                page.locator("#password").fill(acc["password"])
                page.click("button.login-submit")
                page.wait_for_function(
                    "() => !window.location.pathname.includes('/login')",
                    timeout=120000,
                )
                page.wait_for_load_state("networkidle", timeout=90000)
                url = page.url
                on_dashboard = acc["dashboard"] in url
                not_change_pw = "/account/password" not in url
                nav_text = page.locator("nav, aside, .sidebar").first.inner_text(timeout=5000) if page.locator("nav, aside, .sidebar").count() else ""
                no_pev_nutrition = True
                if acc["role"] == "Admin clinique":
                    lower = nav_text.lower()
                    no_pev_nutrition = "pev" not in lower and "vaccination" not in lower and "nutrition" not in lower
                ok = on_dashboard and not_change_pw and no_pev_nutrition
                shot = OUT / f"{slug}.png"
                page.screenshot(path=str(shot), full_page=True)
                detail = url if ok else f"expected {acc['dashboard']}, got {url}"
                if not no_pev_nutrition:
                    detail = "PEV/Nutrition visible in nav"
                proofs.append((acc["role"], ok, detail, str(shot.name)))
            except Exception as exc:
                proofs.append((acc["role"], False, str(exc)[:120], ""))
            finally:
                page.close()
        browser.close()
    return proofs


def main() -> int:
    print("=== Step 1: Reset passwords via platform API ===")
    token = login_admin()
    reset_results = reset_passwords(token)
    for role, email, ok, detail in reset_results:
        print(f"[{'PASS' if ok else 'FAIL'}] reset {role} {email} -> {detail}")

    print("\n=== Step 2: API login verification ===")
    api_results = []
    for acc in REAL_STAFF:
        ok, detail = api_login(acc["email"], acc["password"])
        api_results.append((acc["role"], ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] API {acc['role']} {acc['email']} — {detail}")

    print("\n=== Step 3: Browser login + dashboard proof ===")
    browser_results = browser_proof()
    for role, ok, detail, shot in browser_results:
        print(f"[{'PASS' if ok else 'FAIL'}] UI {role} — {detail}" + (f" [{shot}]" if shot else ""))

    all_ok = (
        all(r[2] for r in reset_results)
        and all(r[1] for r in api_results)
        and all(r[1] for r in browser_results)
    )
    print(f"\nOverall: {'PASS' if all_ok else 'FAIL'}")
    print(f"Screenshots: {OUT}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
