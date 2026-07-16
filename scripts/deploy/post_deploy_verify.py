#!/usr/bin/env python3
"""Post-deploy smoke tests for Railway + Vercel staging."""

from __future__ import annotations

import argparse
import sys
import uuid

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
    print(f"[OK] GET /health -> {body}")


def check_ready(base: str) -> None:
    r = httpx.get(f"{base.rstrip('/')}/health/ready", timeout=30.0)
    r.raise_for_status()
    print(f"[OK] GET /health/ready -> {r.json()}")


def check_auth(base: str, email: str, password: str) -> str:
    r = httpx.post(
        f"{base.rstrip('/')}/auth/login",
        data={"username": email, "password": password},
        timeout=30.0,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    assert token, r.text
    print(f"[OK] POST /auth/login -> {email}")
    return token


def check_clinic_isolation(base: str) -> None:
    """Verify clinic B cannot see clinic A patients."""
    token_alpha = check_auth(base, "reception.demo@sante-gn.test", "ReceptionDemo1!")
    token_beta = check_auth(base, "reception.beta@sante-gn.test", "ReceptionBeta1!")

    unique_tag = f"DeployIso{uuid.uuid4().hex[:8]}"
    phone = f"+22462{uuid.uuid4().int % 10**7:07d}"
    r = httpx.post(
        f"{base.rstrip('/')}/clinical/reception/patients",
        json={
            "first_name": "Alpha",
            "last_name": unique_tag,
            "age": 42,
            "gender": "F",
            "phone": phone,
            "mother_name": "Mère Deploy",
            "visit_destination": "Consultation externe",
        },
        headers={"Authorization": f"Bearer {token_alpha}"},
        timeout=30.0,
    )
    assert r.status_code == 201, r.text
    patient_id = r.json()["id"]

    r = httpx.get(
        f"{base.rstrip('/')}/clinical/reception/patients",
        params={"q": unique_tag},
        headers={"Authorization": f"Bearer {token_beta}"},
        timeout=30.0,
    )
    assert r.status_code == 200, r.text
    ids_beta = {row["id"] for row in r.json()}
    assert patient_id not in ids_beta, f"Clinic B leaked patient {patient_id}"

    r = httpx.get(
        f"{base.rstrip('/')}/clinical/reception/patients",
        params={"q": unique_tag},
        headers={"Authorization": f"Bearer {token_alpha}"},
        timeout=30.0,
    )
    assert r.status_code == 200, r.text
    ids_alpha = {row["id"] for row in r.json()}
    assert patient_id in ids_alpha
    print("[OK] Multi-tenant clinic isolation verified")


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
        check_clinic_isolation(args.backend)
        if args.frontend:
            r = httpx.get(args.frontend.rstrip("/") + "/", timeout=30.0, follow_redirects=True)
            r.raise_for_status()
            print(f"[OK] Frontend reachable -> {args.frontend}")
        print("=== All smoke checks passed ===")
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
