#!/usr/bin/env python3
"""Verify auth session UX on deployed backend (login, profile, isolation)."""

from __future__ import annotations

import argparse
import sys
import uuid

import httpx

ACCOUNTS = [
    ("platform.admin@sante-gn.test", "PlatformAdmin1!", "platform_admin"),
    ("reception.demo@sante-gn.test", "ReceptionDemo1!", "receptionist"),
    ("reception.beta@sante-gn.test", "ReceptionBeta1!", "receptionist"),
    ("doctor.demo@sante-gn.test", "DoctorDemo1!", "doctor"),
    ("clinic.admin.a@sante-gn.test", "ClinicAdminA1!", "clinic_admin"),
]


def login(base: str, email: str, password: str) -> str:
    r = httpx.post(
        f"{base.rstrip('/')}/auth/login",
        data={"username": email, "password": password},
        timeout=30.0,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    assert token, r.text
    return token


def check_me(base: str, token: str, expected_role: str) -> dict:
    r = httpx.get(
        f"{base.rstrip('/')}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    r.raise_for_status()
    body = r.json()
    assert body.get("role") == expected_role, body
    assert body.get("full_name"), body
    print(f"[OK] /auth/me -> {body['email']} role={body['role']} clinic={body.get('clinic_name')}")
    return body


def check_logout_blocks(base: str) -> None:
    r = httpx.get(f"{base.rstrip('/')}/auth/me", timeout=30.0)
    assert r.status_code == 401, r.text
    print("[OK] /auth/me blocked without token")


def check_isolation(base: str) -> None:
    token_alpha = login(base, "reception.demo@sante-gn.test", "ReceptionDemo1!")
    token_beta = login(base, "reception.beta@sante-gn.test", "ReceptionBeta1!")
    tag = f"AuthSess{uuid.uuid4().hex[:8]}"
    phone = f"+22462{uuid.uuid4().int % 10**7:07d}"

    r = httpx.post(
        f"{base.rstrip('/')}/clinical/reception/patients",
        json={
            "first_name": "Alpha",
            "last_name": tag,
            "age": 40,
            "gender": "F",
            "phone": phone,
        },
        headers={"Authorization": f"Bearer {token_alpha}"},
        timeout=30.0,
    )
    assert r.status_code == 201, r.text
    patient_id = r.json()["id"]

    r = httpx.get(
        f"{base.rstrip('/')}/clinical/reception/patients",
        params={"q": tag},
        headers={"Authorization": f"Bearer {token_beta}"},
        timeout=30.0,
    )
    assert r.status_code == 200, r.text
    assert patient_id not in {row["id"] for row in r.json()}
    print("[OK] Multi-tenant isolation after auth checks")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    args = parser.parse_args()

    try:
        for email, password, role in ACCOUNTS:
            token = login(args.backend, email, password)
            check_me(args.backend, token, role)
        check_logout_blocks(args.backend)
        check_isolation(args.backend)
        print("=== Auth session verification passed ===")
        return 0
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
