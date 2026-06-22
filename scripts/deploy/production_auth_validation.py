#!/usr/bin/env python3
"""Production auth validation for clinic staff onboarding."""

from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"
AASMA_CLINIC_ID = 17
ADMIN_EMAIL = "platform.admin@sante-gn.test"
ADMIN_PASSWORD = "PlatformAdmin1!"

ROLE_HOME = {
    "receptionist": "/clinical/reception",
    "cashier": "/clinical/reception",
    "doctor": "/clinical/doctor",
    "lab_technician": "/clinical/lab",
    "pharmacist": "/clinical/pharmacy",
    "clinic_admin": "/clinical/admin",
}


def api_login(email: str, password: str) -> tuple[bool, dict | None]:
    r = httpx.post(
        f"{BACKEND}/auth/login-json",
        json={"email": email, "password": password},
        timeout=60,
    )
    if r.status_code != 200:
        return False, None
    return True, r.json()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    run_id = uuid.uuid4().hex[:8]
    staff_email = f"aasma.auth.test.{run_id}@field.local"
    staff_password = ""
    new_password = "AasmaNewPass1!"
    reset_password = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # Eye icon on login
        page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded")
        page.locator("#password").fill("TestPass1!")
        toggle = page.locator(".password-input-toggle")
        checks.append(("Login eye toggle exists", toggle.count() > 0, ""))
        if toggle.count():
            type_before = page.locator("#password").get_attribute("type")
            toggle.click()
            type_after = page.locator("#password").get_attribute("type")
            checks.append(
                ("Login eye toggles visibility",
                 type_before == "password" and type_after == "text",
                 f"{type_before}->{type_after}"),
            )

        # Admin login + create staff
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        page.reload()
        page.locator("#email").fill(ADMIN_EMAIL)
        page.locator("#password").fill(ADMIN_PASSWORD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/platform/clinics/{AASMA_CLINIC_ID}/reception", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=90000)
        page.click("button.clinical-btn:has-text('Créer')")
        staff_password = page.locator(".platform-staff-form input[type='text']").input_value()
        page.locator(".platform-staff-form input[type='email']").fill(staff_email)
        page.locator(".platform-staff-form button[type='submit']").click()
        page.wait_for_load_state("networkidle", timeout=90000)

        ok, payload = api_login(staff_email, staff_password)
        checks.append(("Create temp password works for login", ok, staff_email))
        checks.append(
            ("Login flags must_change_password",
             bool(payload and payload.get("must_change_password")),
             str(payload.get("must_change_password") if payload else None)),
        )

        # Staff forced password change
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        page.goto(f"{FRONTEND}/login")
        page.locator("#email").fill(staff_email)
        page.locator("#password").fill(staff_password)
        page.click("button.login-submit")
        page.wait_for_url("**/account/password**", timeout=120000)
        checks.append(("Temp login redirects to change password", "/account/password" in page.url, page.url))
        page.locator("#current-password").fill(staff_password)
        page.locator("#new-password").fill(new_password)
        page.locator("#confirm-password").fill(new_password)
        page.click("button.account-submit")
        page.wait_for_function(
            "() => !window.location.pathname.includes('/account/password')",
            timeout=120000,
        )
        checks.append(("After change lands on dashboard", "/clinical/reception" in page.url, page.url))

        ok_new, _ = api_login(staff_email, new_password)
        checks.append(("Login with new password works", ok_new, ""))
        ok_old, _ = api_login(staff_email, staff_password)
        checks.append(("Old temp password rejected", not ok_old, ""))

        # Admin reset flow
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        page.goto(f"{FRONTEND}/login")
        page.locator("#email").fill(ADMIN_EMAIL)
        page.locator("#password").fill(ADMIN_PASSWORD)
        page.click("button.login-submit")
        page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
        page.goto(f"{FRONTEND}/platform/clinics/{AASMA_CLINIC_ID}/reception")
        page.wait_for_load_state("networkidle", timeout=90000)
        pw_before = page.locator(f"tr:has-text('{staff_email}') td").nth(2).inner_text()
        page.locator(f"tr:has-text('{staff_email}') button:has-text('Réinitialiser')").click()
        page.click("button:has-text('Confirmer la réinitialisation')")
        page.wait_for_selector(".platform-modal input[readonly]", timeout=30000)
        reset_password = page.locator(".platform-modal input[readonly]").input_value()
        page.click("button:has-text('Fermer')")
        pw_after = page.locator(f"tr:has-text('{staff_email}') td").nth(2).inner_text()
        checks.append(("Reset shows copy + new password", len(reset_password) >= 8, reset_password))
        checks.append(("Reset updates session display only", pw_after == reset_password, pw_after))
        ok_reset, _ = api_login(staff_email, reset_password)
        checks.append(("Reset password works for login", ok_reset, ""))
        ok_prev, _ = api_login(staff_email, new_password)
        checks.append(("Previous password rejected after reset", not ok_prev, ""))

        page.reload()
        page.wait_for_load_state("networkidle", timeout=90000)
        pw_reload = page.locator(f"tr:has-text('{staff_email}') td").nth(2).inner_text()
        checks.append(("No regeneration on refresh", pw_reload == reset_password, pw_reload))

        browser.close()

    failed = sum(1 for _, ok, _ in checks if not ok)
    print("\n# Production auth validation\n")
    print("| Check | Result | Detail |")
    print("|-------|--------|--------|")
    for name, ok, detail in checks:
        print(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    print(f"\nOverall: {'PASS' if failed == 0 else 'FAIL'} ({len(checks)-failed}/{len(checks)})")
    print(f"URL: {FRONTEND}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
