#!/usr/bin/env python3
"""End-to-end Priority 1 production test (nutrition + PEV + auth reset + staff)."""

from __future__ import annotations

import sys
import uuid
from datetime import date, timedelta

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"


def login(email: str, password: str) -> tuple[str, dict]:
    r = httpx.post(
        f"{BACKEND}/auth/login-json",
        json={"email": email, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    me = httpx.get(
        f"{BACKEND}/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
        timeout=30,
    ).json()
    return data["access_token"], me


def main() -> int:
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        line = f"[{'OK' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else "")
        print(line)
        if not cond:
            ok = False

    suffix = uuid.uuid4().hex[:8]
    admin_token, admin_me = login("clinic.admin.a@sante-gn.test", "ClinicAdminA1!")
    clinic_id = admin_me["clinic_id"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Multi-staff: create nutritionist
    nutri_email = f"nutri.{suffix}.{uuid.uuid4().hex[:6]}@sante-gn.test"
    r = httpx.post(
        f"{BACKEND}/clinical/staff",
        json={
            "email": nutri_email,
            "password": "NutriProd1!",
            "role": "nutritionist",
            "clinic_id": clinic_id,
        },
        headers=headers,
        timeout=30,
    )
    if r.status_code == 201:
        check("Create nutritionist staff", True, nutri_email)
        assess_token, _ = login(nutri_email, "NutriProd1!")
    else:
        check("Create nutritionist staff", False, f"{r.status_code} {r.text[:80]}")
        assess_token = admin_token
        print("[WARN] Using clinic admin for nutrition assessment")

    r = httpx.get(
        f"{BACKEND}/clinical/staff",
        params={"clinic_id": clinic_id},
        headers=headers,
        timeout=30,
    )
    check("List clinic staff", r.status_code == 200 and len(r.json()) >= 3, f"count={len(r.json())}")

    # 2. Patient intake + nutrition
    recv_token, _ = login("reception.demo@sante-gn.test", "ReceptionDemo1!")
    r = httpx.post(
        f"{BACKEND}/clinical/reception/patients",
        json={
            "first_name": "Prod",
            "last_name": f"Nutri{suffix}",
            "age": 2,
            "gender": "F",
            "phone": f"+22462{uuid.uuid4().int % 10**7:07d}",
            "date_of_birth": (date.today() - timedelta(days=800)).isoformat(),
        },
        headers={"Authorization": f"Bearer {recv_token}"},
        timeout=30,
    )
    check("Patient intake", r.status_code == 201, r.text[:80])
    patient_id = r.json()["id"] if r.status_code == 201 else 0

    r = httpx.post(
        f"{BACKEND}/clinical/nutrition/assessments",
        json={
            "patient_id": patient_id,
            "weight_kg": 11.2,
            "height_cm": 84.0,
            "muac_cm": 12.8,
            "age_months": 26,
        },
        headers={"Authorization": f"Bearer {assess_token}"},
        timeout=30,
    )
    check("Record nutrition assessment", r.status_code == 201, r.json().get("nutritional_status", r.text[:80]))

    r = httpx.get(
        f"{BACKEND}/clinical/nutrition/patients/{patient_id}/history",
        headers={"Authorization": f"Bearer {assess_token}"},
        timeout=30,
    )
    check("Nutrition history", r.status_code == 200 and len(r.json()) >= 1, f"rows={len(r.json())}")

    # 3. PEV immunization
    r = httpx.get(
        f"{BACKEND}/clinical/immunization/patients/{patient_id}/status",
        headers={"Authorization": f"Bearer {recv_token}"},
        timeout=30,
    )
    status = r.json() if r.status_code == 200 else {}
    check(
        "PEV due/missed status",
        r.status_code == 200 and "missed" in status,
        f"missed={len(status.get('missed', []))} due={len(status.get('due', []))}",
    )

    if status.get("due") or status.get("missed"):
        v = (status.get("missed") or status.get("due"))[0]
        r = httpx.post(
            f"{BACKEND}/clinical/immunization/records",
            json={
                "patient_id": patient_id,
                "vaccine_code": v["vaccine_code"],
                "vaccine_name": v["vaccine_name"],
                "dose_label": v["dose_label"],
                "administered_at": date.today().isoformat(),
            },
            headers={"Authorization": f"Bearer {recv_token}"},
            timeout=30,
        )
        check("Record vaccination", r.status_code == 201, v["vaccine_code"])

    # 4. Password reset
    reset_email = f"reset.prod.{suffix}@example.com"
    r = httpx.post(
        f"{BACKEND}/auth/register",
        json={"email": reset_email, "password": "OldProdPass1!", "role": "patient"},
        timeout=30,
    )
    check("Register test patient for reset", r.status_code == 201, reset_email)

    r = httpx.post(f"{BACKEND}/auth/forgot-password", json={"email": reset_email}, timeout=30)
    check("Forgot password", r.status_code == 200)

    r = httpx.post(
        f"{BACKEND}/auth/reset-password",
        json={"token": "invalid-token-for-e2e", "new_password": "NewProdPass1!"},
        timeout=30,
    )
    check("Reset password rejects invalid token", r.status_code == 400, r.text[:60])

    r = httpx.post(
        f"{BACKEND}/auth/login-json",
        json={"email": reset_email, "password": "OldProdPass1!"},
        timeout=30,
    )
    check("Patient login still works after forgot request", r.status_code == 200)

    print(f"\nFrontend: {FRONTEND}")
    print(f"Backend:  {BACKEND}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
