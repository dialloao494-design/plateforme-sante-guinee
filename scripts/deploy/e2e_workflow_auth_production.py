#!/usr/bin/env python3
"""Production smoke: auth signup/login + visit workflow queues."""

from __future__ import annotations

import sys
import uuid

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://frontend-seven-rust-94.vercel.app"


def login(email: str, password: str) -> str:
    r = httpx.post(
        f"{BACKEND}/auth/login-json",
        json={"email": email, "password": password},
        timeout=45,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        print(f"[{'OK' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not cond:
            ok = False

    # Health
    r = httpx.get(f"{BACKEND}/health", timeout=30)
    check("Backend health", r.status_code == 200, r.text[:60])

    # Doctor signup with strong password → token + immediate login
    suffix = uuid.uuid4().hex[:10]
    doc_email = f"doctor.e2e.{suffix}@sante-gn.test"
    doc_pass = "TestDoctor1!"
    r = httpx.post(
        f"{BACKEND}/auth/register",
        json={"email": doc_email, "password": doc_pass, "role": "doctor"},
        timeout=45,
    )
    check("Doctor register 201", r.status_code == 201, r.text[:120])
    if r.status_code == 201:
        body = r.json()
        check("Register returns access_token", bool(body.get("access_token")))
        check("Register returns doctor_id", body.get("doctor_id") is not None)
        try:
            login(doc_email, doc_pass)
            check("Login after signup", True)
        except Exception as exc:
            check("Login after signup", False, str(exc))

    # Weak password rejected
    r = httpx.post(
        f"{BACKEND}/auth/register",
        json={"email": f"weak.{suffix}@sante-gn.test", "password": "short", "role": "doctor"},
        timeout=30,
    )
    check("Weak password rejected", r.status_code == 422)

    # Duplicate email
    r = httpx.post(
        f"{BACKEND}/auth/register",
        json={"email": doc_email, "password": doc_pass, "role": "doctor"},
        timeout=30,
    )
    check("Duplicate email rejected", r.status_code in (400, 409, 422))

    # Forgot password (always 200 to avoid enumeration)
    r = httpx.post(
        f"{BACKEND}/auth/forgot-password",
        json={"email": "reception.demo@sante-gn.test"},
        timeout=30,
    )
    check("Forgot password endpoint", r.status_code == 200)

    # Reset with invalid token
    r = httpx.post(
        f"{BACKEND}/auth/reset-password",
        json={"token": "invalid-token", "new_password": "NewPass123!"},
        timeout=30,
    )
    check("Reset invalid token rejected", r.status_code in (400, 404, 422))

    # Workflow: reception starts child visit, advances to nutrition
    recv_token = login("reception.demo@sante-gn.test", "ReceptionDemo1!")
    recv_h = {"Authorization": f"Bearer {recv_token}"}
    r = httpx.post(
        f"{BACKEND}/clinical/reception/patients",
        json={
            "first_name": "WF",
            "last_name": suffix,
            "age": 6,
            "gender": "M",
            "phone": f"+224622{suffix[:6]}",
        },
        headers=recv_h,
        timeout=45,
    )
    check("Create patient", r.status_code == 201, r.text[:80])
    if r.status_code != 201:
        print(f"\nFrontend: {FRONTEND}")
        return 1
    patient_id = r.json()["id"]

    r = httpx.post(
        f"{BACKEND}/clinical/workflow/visits",
        json={"patient_id": patient_id, "workflow_type": "child"},
        headers=recv_h,
        timeout=45,
    )
    check("Start child visit", r.status_code == 201, r.text[:120])
    if r.status_code != 201:
        print(f"\nFrontend: {FRONTEND}")
        return 1
    wf_id = r.json()["id"]
    check("Visit at reception", r.json().get("current_department") == "reception")

    r = httpx.post(
        f"{BACKEND}/clinical/workflow/visits/{wf_id}/complete/reception",
        headers=recv_h,
        timeout=45,
    )
    check("Complete reception step", r.status_code == 200, r.text[:80])
    if r.status_code == 200:
        check("Advanced to nutrition", r.json().get("current_department") == "nutrition")

    print(f"\nBackend: {BACKEND}")
    print(f"Frontend: {FRONTEND}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
