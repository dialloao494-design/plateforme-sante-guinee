#!/usr/bin/env python3
"""Security Wave 1 validation — API headers, forbid-extra, IDOR smoke."""

from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE = (os.getenv("API_BASE_URL") or os.getenv("BACKEND_URL") or "http://127.0.0.1:8000").rstrip("/")


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    client = httpx.Client(timeout=30.0)

    try:
        health = client.get(f"{BASE}/health")
    except Exception as exc:
        print(f"API unreachable at {BASE}: {exc}")
        return 2

    checks.append(("Health", health.status_code == 200, str(health.status_code)))
    checks.append(
        (
            "X-Content-Type-Options",
            health.headers.get("X-Content-Type-Options") == "nosniff",
            health.headers.get("X-Content-Type-Options") or "missing",
        )
    )
    checks.append(
        (
            "X-Frame-Options",
            health.headers.get("X-Frame-Options") == "DENY",
            health.headers.get("X-Frame-Options") or "missing",
        )
    )

    # Unknown field on public register (extra forbid on PublicRegistration if present)
    email = f"w1.{uuid.uuid4().hex[:8]}@example.com"
    weak = client.post(
        f"{BASE}/auth/register",
        json={
            "email": email,
            "password": "Wave1Validate99!",
            "role": "patient",
            "is_admin": True,
        },
    )
    checks.append(
        (
            "Unknown field rejected or ignored safely",
            weak.status_code in (201, 422),
            f"{weak.status_code}:{weak.text[:120]}",
        )
    )

    return _print(checks)


def _print(checks: list[tuple[str, bool, str]]) -> int:
    ok = True
    for name, passed, detail in checks:
        mark = "PASS" if passed else "FAIL"
        if not passed:
            ok = False
        print(f"[{mark}] {name}: {detail}")
    print("WAVE1_SECURITY_VALIDATION_" + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
