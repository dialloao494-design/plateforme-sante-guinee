#!/usr/bin/env python3
"""Reassign Koloma midwife accounts to pev_agent and nurse roles."""

from __future__ import annotations

import sys

import httpx

BASE = "https://web-production-ad6a36.up.railway.app"
CLINIC_ID = 13
ADMIN_EMAIL = "platform.admin@sante-gn.test"
ADMIN_PASSWORD = "PlatformAdmin1!"

REASSIGNMENTS = [
    ("infirmsadjo01@gmail.com", "nurse"),
    ("bahalim1843@gmail.com", "nurse"),
    ("niepousalomonloua@gmail.com", "pev_agent"),
    ("bahkadiatoudongoltouma@gmail.com", "pev_agent"),
    ("fatmataconate8@gmail.com", "pev_agent"),
    ("soumahsoumah773@gmail.com", "pev_agent"),
]


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=60.0) as client:
        login = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        if login.status_code != 200:
            print(f"LOGIN FAIL: {login.status_code} {login.text}")
            return 1
        token = login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        staff = client.get("/clinical/staff", params={"clinic_id": CLINIC_ID}, headers=headers)
        if staff.status_code != 200:
            print(f"STAFF LIST FAIL: {staff.status_code} {staff.text}")
            return 1
        by_email = {u["email"].lower(): u for u in staff.json()}

        ok = 0
        for email, role in REASSIGNMENTS:
            user = by_email.get(email.lower())
            if not user:
                print(f"SKIP {email}: not found")
                continue
            resp = client.patch(
                f"/clinical/staff/{user['id']}/role",
                json={"role": role, "clinic_id": CLINIC_ID},
                headers=headers,
            )
            if resp.status_code == 200:
                print(f"PASS {email} -> {role}")
                ok += 1
            else:
                print(f"FAIL {email}: {resp.status_code} {resp.text}")

        print(f"\n{ok}/{len(REASSIGNMENTS)} role updates OK")
        return 0 if ok == len(REASSIGNMENTS) else 1


if __name__ == "__main__":
    sys.exit(main())
