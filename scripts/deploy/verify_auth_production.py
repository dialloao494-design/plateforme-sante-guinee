#!/usr/bin/env python3
"""Production auth smoke: login + /auth/me for core roles."""

from __future__ import annotations

import sys

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://frontend-seven-rust-94.vercel.app"

ACCOUNTS = [
    ("clinic_admin", "clinic.admin.a@sante-gn.test", "ClinicAdminA1!", "/clinical/admin"),
    ("reception", "reception.demo@sante-gn.test", "ReceptionDemo1!", "/clinical/reception"),
    ("doctor_cis", "doctor.demo@sante-gn.test", "DoctorDemo1!", "/clinical/doctor"),
]


def main() -> int:
    base = BACKEND.rstrip("/")
    fails = 0
    print("=== Frontend routes ===")
    for route in ["/login", "/signup", "/platform", "/doctor/dashboard", "/clinical/reception"]:
        r = httpx.get(FRONTEND + route, timeout=30, follow_redirects=True)
        print(f"  GET {route} -> {r.status_code}")

    print("\n=== Auth API ===")
    for label, email, password, _home in ACCOUNTS:
        login = httpx.post(
            f"{base}/auth/login-json",
            json={"email": email, "password": password},
            timeout=45,
        )
        ok = login.status_code == 200 and login.json().get("access_token")
        print(f"  {label} login:", login.status_code, "token" if ok else login.text[:120])
        if not ok:
            fails += 1
            continue
        tok = login.json()["access_token"]
        me = httpx.get(f"{base}/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        print(f"  {label} me:", me.status_code, me.text[:160])
        if me.status_code != 200:
            fails += 1

    # doctor public signup path
    print("\n=== Doctor register smoke ===")
    import uuid

    s = uuid.uuid4().hex[:8]
    email = f"smoke.doc.{s}@sante-gn.test"
    pwd = "SmokeDoctor1!"
    reg = httpx.post(
        f"{base}/auth/register",
        json={"email": email, "password": pwd, "role": "doctor"},
        timeout=45,
    )
    print("  register:", reg.status_code, reg.json().get("role") if reg.status_code == 201 else reg.text[:120])
    if reg.status_code != 201:
        fails += 1
    else:
        tok = reg.json()["access_token"]
        me = httpx.get(f"{base}/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
        print("  me:", me.status_code, me.json().get("role"), "clinic_id=", me.json().get("clinic_id"))

    print("\n=== Email health ===")
    eh = httpx.get(f"{base}/health/email", timeout=30)
    print(" ", eh.text)

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
