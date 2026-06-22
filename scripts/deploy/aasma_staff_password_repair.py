#!/usr/bin/env python3
"""Reset real Clinique AASMA staff passwords in production."""

from __future__ import annotations

import re
import secrets
import string
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASE = "https://web-production-ad6a36.up.railway.app"
AASMA_CLINIC_ID = 17
ADMIN_EMAIL = "platform.admin@sante-gn.test"
ADMIN_PASSWORD = "PlatformAdmin1!"

TARGET_ROLES = ["clinic_admin", "receptionist", "doctor", "lab_technician", "pharmacist", "cashier"]

TEST_PATTERNS = (
    r"@aasma-clinic\.gn$",
    r"@field\.local$",
    r"field\.verify",
    r"field\.probe",
    r"pwtest",
    r"@sante-gn\.test$",
)


def gen_password(prefix: str = "Aasma") -> str:
    chars = string.ascii_letters + string.digits
    tail = "".join(secrets.choice(chars) for _ in range(8))
    return f"{prefix}{tail}1!"


def is_test_email(email: str) -> bool:
    e = email.lower()
    return any(re.search(p, e) for p in TEST_PATTERNS)


def login() -> str:
    r = httpx.post(
        f"{BASE}/auth/login-json",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def verify_login(email: str, password: str) -> bool:
    r = httpx.post(
        f"{BASE}/auth/login-json",
        json={"email": email, "password": password},
        timeout=60,
    )
    return r.status_code == 200


def main() -> int:
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    staff = httpx.get(
        f"{BASE}/platform/clinics/{AASMA_CLINIC_ID}/staff",
        headers=headers,
        timeout=60,
    ).json()

    real = [s for s in staff if not is_test_email(s["email"]) and s.get("is_active")]
    by_role: dict[str, dict] = {}
    for member in real:
        role = member["role"]
        if role not in by_role:
            by_role[role] = member

    results: list[tuple[str, str, str, str, bool]] = []
    for role in TARGET_ROLES:
        member = by_role.get(role)
        if not member:
            results.append((role, "—", "MISSING", "—", False))
            continue
        password = gen_password("Aasma")
        r = httpx.post(
            f"{BASE}/platform/clinics/{AASMA_CLINIC_ID}/staff/{member['id']}/reset-password",
            headers=headers,
            json={"new_password": password},
            timeout=60,
        )
        ok = r.status_code == 200 and verify_login(member["email"], password)
        results.append((role, member["email"], password, str(r.status_code), ok))

    print("# AASMA staff password repair\n")
    print("| Role | Email | Temp password | HTTP | Login OK |")
    print("|------|-------|---------------|------|----------|")
    for role, email, pw, status, ok in results:
        print(f"| {role} | {email} | `{pw}` | {status} | {'PASS' if ok else 'FAIL'} |")

    failed = sum(1 for *_, ok in results if not ok)
    print(f"\nOverall: {'PASS' if failed == 0 else 'FAIL'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
