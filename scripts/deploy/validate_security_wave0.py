#!/usr/bin/env python3
"""Security Wave 0 validation — identity hardening smoke checks against a live API."""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE = (os.getenv("API_BASE_URL") or os.getenv("BACKEND_URL") or "http://127.0.0.1:8000").rstrip("/")


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    client = httpx.Client(timeout=30.0, follow_redirects=True)

    # Health
    try:
        r = client.get(f"{BASE}/health")
        checks.append(("Health", r.status_code == 200, str(r.status_code)))
    except Exception as exc:
        print(f"API unreachable at {BASE}: {exc}")
        return 2

    email = f"wave0.val.{uuid.uuid4().hex[:8]}@example.com"
    password = "Wave0Validate99!"

    r = client.post(
        f"{BASE}/auth/register",
        json={"email": email, "password": password, "role": "patient"},
    )
    checks.append(("Register with strong password", r.status_code == 201, r.text[:200]))
    if r.status_code != 201:
        _print(checks)
        return 1
    body = r.json()
    checks.append(("Register returns refresh_token", bool(body.get("refresh_token")), str(bool(body.get("refresh_token")))))
    access = body["access_token"]
    refresh = body.get("refresh_token")

    weak = client.post(
        f"{BASE}/auth/register",
        json={"email": f"weak.{uuid.uuid4().hex[:6]}@example.com", "password": "Short1!", "role": "patient"},
    )
    checks.append(("Weak password rejected", weak.status_code == 422, weak.text[:200]))

    if refresh:
        rotated = client.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh})
        checks.append(("Refresh rotates", rotated.status_code == 200, rotated.text[:200]))
        if rotated.status_code == 200:
            refresh2 = rotated.json().get("refresh_token")
            reuse = client.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh})
            checks.append(("Refresh reuse rejected", reuse.status_code == 401, reuse.text[:200]))
            refresh = refresh2 or refresh
            access = rotated.json().get("access_token") or access

    me = client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {access}"})
    checks.append(("/auth/me with access token", me.status_code == 200, me.text[:200]))

    out = client.post(
        f"{BASE}/auth/logout",
        json={"refresh_token": refresh} if refresh else {},
        headers={"Authorization": f"Bearer {access}"},
    )
    checks.append(("Logout", out.status_code == 200, out.text[:200]))
    me2 = client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {access}"})
    checks.append(("Access token denied after logout", me2.status_code == 401, me2.text[:200]))

    return _print(checks)


def _print(checks: list[tuple[str, bool, str]]) -> int:
    ok = True
    for name, passed, detail in checks:
        mark = "PASS" if passed else "FAIL"
        if not passed:
            ok = False
        print(f"[{mark}] {name}: {detail}")
    print("WAVE0_SECURITY_VALIDATION_" + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
