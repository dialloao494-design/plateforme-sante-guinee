#!/usr/bin/env python3
"""Verify independent auth sessions across four browser tabs in production."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND = "https://plateforme-sante-guinee.vercel.app"

TABS = [
    ("reception", "baldoumar14@gmail.com", "AasmaRecep1!", "/clinical/reception", "receptionist"),
    ("lab", "mamadoudianbarry06@gmail.com", "AasmaLab1!", "/clinical/lab", "lab_technician"),
    ("pharmacy", "ben752231@gmail.com", "AasmaPharm1!", "/clinical/pharmacy", "pharmacist"),
    ("admin", "contactpolycliniqueaasma@gmail.com", "AasmaAdmin1!", "/clinical/admin", "clinic_admin"),
]


def login(page, email: str, password: str, home: str) -> None:
    page.goto(f"{FRONTEND}/login", wait_until="domcontentloaded", timeout=120000)
    page.locator("#email").wait_for(state="visible", timeout=60000)
    page.locator("#email").fill(email)
    page.locator("#password").fill(password)
    page.click("button.login-submit")
    page.wait_for_function("() => !window.location.pathname.includes('/login')", timeout=120000)
    page.goto(f"{FRONTEND}{home}", wait_until="networkidle", timeout=120000)


def tab_state(page) -> dict:
    return page.evaluate(
        """() => ({
            path: window.location.pathname,
            user_id: sessionStorage.getItem('user_id'),
            user_role: sessionStorage.getItem('user_role'),
            tab_token: Boolean(sessionStorage.getItem('token') || sessionStorage.getItem('access_token')),
            shared_token: Boolean(localStorage.getItem('token') || localStorage.getItem('access_token')),
        })"""
    )


def assert_tab(name: str, page, expected_role: str, expected_path: str) -> tuple[bool, str]:
    state = tab_state(page)
    body = page.locator("body").inner_text(timeout=8000)
    blocked = "Profil inaccessible" in body or "Profil utilisateur vide" in body
    on_login = "/login" in state["path"]
    role_ok = state["user_role"] == expected_role
    path_ok = expected_path in state["path"]
    ok = state["tab_token"] and not on_login and not blocked and role_ok and path_ok
    detail = (
        f"path={state['path']} role={state['user_role']} uid={state['user_id']} "
        f"tab_token={state['tab_token']} shared_token={state['shared_token']} blocked={blocked}"
    )
    return ok, detail


def hard_reload(page) -> None:
    cdp = page.context.new_cdp_session(page)
    cdp.send("Page.reload", {"ignoreCache": True})
    page.wait_for_function("() => document.readyState === 'complete'", timeout=120000)
    page.wait_for_load_state("networkidle", timeout=120000)
    page.wait_for_timeout(500)


def main() -> int:
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        pages = [context.new_page() for _ in range(4)]

        for page, (name, email, password, home, role) in zip(pages, TABS):
            login(page, email, password, home)
            ok, detail = assert_tab(name, page, role, home)
            results.append({"role": name, "test": "login", "pass": ok, "detail": detail})

        roles_after_login = [tab_state(pg)["user_role"] for pg in pages]
        unique_roles = len(set(roles_after_login)) == 4
        results.append(
            {
                "role": "all",
                "test": "distinct_roles_after_login",
                "pass": unique_roles,
                "detail": ",".join(roles_after_login or ["none"]),
            }
        )

        for page, (name, _e, _p, home, role) in zip(pages, TABS):
            page.reload(wait_until="networkidle")
            ok, detail = assert_tab(name, page, role, home)
            results.append({"role": name, "test": "normal_refresh", "pass": ok, "detail": detail})

        for page, (name, _e, _p, home, role) in zip(pages, TABS):
            hard_reload(page)
            ok, detail = assert_tab(name, page, role, home)
            results.append({"role": name, "test": "hard_refresh", "pass": ok, "detail": detail})

        pages[0].get_by_role("button", name="Déconnexion").click()
        pages[0].wait_for_function("() => window.location.pathname.includes('/login')", timeout=60000)

        ok_logout, detail_logout = assert_tab("reception", pages[0], "receptionist", "/clinical/reception")
        results.append(
            {
                "role": "reception",
                "test": "logout_tab1",
                "pass": not ok_logout and "/login" in tab_state(pages[0])["path"],
                "detail": detail_logout,
            }
        )

        for page, (name, _e, _p, home, role) in zip(pages[1:], TABS[1:]):
            ok, detail = assert_tab(name, page, role, home)
            results.append({"role": name, "test": "after_other_tab_logout", "pass": ok, "detail": detail})

        context.close()
        browser.close()

    out = Path(__file__).resolve().parents[2] / "docs" / "MULTI_TAB_SESSION_PROOF.json"
    out.write_text(
        json.dumps({"frontend": FRONTEND, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    failed = [r for r in results if not r["pass"]]
    for row in results:
        status = "PASS" if row["pass"] else "FAIL"
        print(f"{status} {row['role']:10} {row['test']:28} {row['detail']}")

    print(f"\nTotal: {len(results) - len(failed)}/{len(results)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
