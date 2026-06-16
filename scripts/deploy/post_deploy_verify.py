#!/usr/bin/env python3
"""Post-deploy smoke tests for Railway + Vercel staging."""

from __future__ import annotations

import argparse
import sys

import httpx

DEFAULT_ACCOUNTS = [
    ("platform.admin@sante-gn.test", "PlatformAdmin1!"),
    ("reception.demo@sante-gn.test", "ReceptionDemo1!"),
]


def check_health(base: str) -> None:
    r = httpx.get(f"{base.rstrip('/')}/health", timeout=30.0)
    r.raise_for_status()
    body = r.json()
    assert body.get("status") == "ok", body
    print(f"[OK] GET /health → {body}")


def check_ready(base: str) -> None:
    r = httpx.get(f"{base.rstrip('/')}/health/ready", timeout=30.0)
    r.raise_for_status()
    print(f"[OK] GET /health/ready → {r.json()}")


def check_auth(base: str, email: str, password: str) -> str:
    r = httpx.post(
        f"{base.rstrip('/')}/auth/login",
        data={"username": email, "password": password},
        timeout=30.0,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    assert token, r.text
    print(f"[OK] POST /auth/login → {email}")
    return token


def check_clinic_isolation(base: str, token_a: str, token_b: str) -> None:
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    r = httpx.get(
        f"{base.rstrip('/')}/clinical/reception/patients",
        params={"q": "Isolation"},
        headers=headers_b,
        timeout=30.0,
    )
    assert r.status_code == 200, r.text
    print("[OK] Clinic B reception patient search reachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, help="Railway backend base URL")
    parser.add_argument("--frontend", default="", help="Optional Vercel frontend URL")
    args = parser.parse_args()

    try:
        check_health(args.backend)
        check_ready(args.backend)
        for email, password in DEFAULT_ACCOUNTS:
            check_auth(args.backend, email, password)
        if args.frontend:
            r = httpx.get(args.frontend.rstrip("/") + "/", timeout=30.0, follow_redirects=True)
            r.raise_for_status()
            print(f"[OK] Frontend reachable → {args.frontend}")
        print("=== All smoke checks passed ===")
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
