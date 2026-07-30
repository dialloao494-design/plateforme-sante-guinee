#!/usr/bin/env python3
"""Verify auth survives refresh and hard refresh in production."""
from __future__ import annotations
import os


import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND = "https://plateforme-sante-guinee.vercel.app"

ROLES = [
    ("reception", "baldoumar14@gmail.com", os.environ["AASMA_RECEPTION_PASSWORD"], "/clinical/reception"),
    ("lab", "mamadoudianbarry06@gmail.com", os.environ["AASMA_LAB_PASSWORD"], "/clinical/lab"),
    ("pharmacy", "ben752231@gmail.com", os.environ["AASMA_PHARMACY_PASSWORD"], "/clinical/pharmacy"),
    ("admin", "contactpolycliniqueaasma@gmail.com", os.environ["AASMA_ADMIN_PASSWORD"], "/clinical/admin"),
]


def login(page, email: str, password: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
    page.locator("#email").wait_for(state="visible", timeout=60000)
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function(
        "() => !window.location.pathname.includes('/login')",
        timeout=120000,
    )
    page.wait_for_load_state("networkidle", timeout=120000)


def token_present(page) -> bool:
    return bool(
        page.evaluate(
            "() => Boolean(sessionStorage.getItem('token') || sessionStorage.getItem('access_token'))"
        )
    )


def tab_state(page) -> dict:
    return page.evaluate(
        """() => ({
            path: window.location.pathname,
            token: Boolean(sessionStorage.getItem('token') || sessionStorage.getItem('access_token')),
        })"""
    )


def still_authenticated(page, expected_path: str) -> tuple[bool, str]:
    path = page.evaluate("() => window.location.pathname")
    body = page.locator("body").inner_text(timeout=5000)
    blocked = "Profil inaccessible" in body or "Profil utilisateur vide" in body
    on_login = "/login" in path
    has_token = token_present(page)
    ok = has_token and not on_login and not blocked and expected_path in path
    return ok, f"path={path} token={has_token} blocked={blocked}"


def main() -> int:
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for role, email, password, home in ROLES:
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            login(page, email, password)
            ok_login, detail_login = still_authenticated(page, home)
            results.append(
                {"role": role, "test": "login", "pass": ok_login, "detail": detail_login}
            )

            page.reload(wait_until="networkidle")
            ok_refresh, detail_refresh = still_authenticated(page, home)
            results.append(
                {"role": role, "test": "normal_refresh", "pass": ok_refresh, "detail": detail_refresh}
            )

            cdp = ctx.new_cdp_session(page)
            cdp.send("Page.reload", {"ignoreCache": True})
            page.wait_for_function("() => document.readyState === 'complete'", timeout=120000)
            page.wait_for_load_state("networkidle", timeout=120000)
            page.wait_for_timeout(500)
            ok_hard, detail_hard = still_authenticated(page, home)
            results.append(
                {"role": role, "test": "hard_refresh", "pass": ok_hard, "detail": detail_hard}
            )

            tab2 = ctx.new_page()
            tab2.goto(f"{FRONTEND}{home}", wait_until="networkidle", timeout=120000)
            tab2_state = tab_state(tab2)
            ok_tab2 = not tab2_state["token"] and "/login" in tab2_state["path"]
            results.append(
                {
                    "role": role,
                    "test": "second_tab_isolated",
                    "pass": ok_tab2,
                    "detail": f"path={tab2_state['path']} token={tab2_state['token']}",
                }
            )

            ok_tab1, detail_tab1 = still_authenticated(page, home)
            results.append(
                {"role": role, "test": "first_tab_after_second", "pass": ok_tab1, "detail": detail_tab1}
            )

            ctx.close()

    out = Path(__file__).resolve().parents[2] / "docs" / "SESSION_PERSISTENCE_PROOF.json"
    out.write_text(json.dumps({"frontend": FRONTEND, "results": results}, indent=2), encoding="utf-8")

    failed = [r for r in results if not r["pass"]]
    for row in results:
        status = "PASS" if row["pass"] else "FAIL"
        print(f"{status} {row['role']:10} {row['test']:22} {row['detail']}")

    print(f"\nTotal: {len(results) - len(failed)}/{len(results)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
