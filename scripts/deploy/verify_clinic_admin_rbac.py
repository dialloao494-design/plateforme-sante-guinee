#!/usr/bin/env python3
"""Verify clinic_admin RBAC on production (or --backend URL)."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BACKEND = "https://web-production-ad6a36.up.railway.app"
CLINIC_ADMIN = ("clinic.admin.a@sante-gn.test", "ClinicAdminA1!")


def login(base: str, email: str, password: str) -> tuple[str | None, str]:
    data = urllib.parse.urlencode({"username": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{base}/auth/login",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read())
            return payload["access_token"], ""
    except urllib.error.HTTPError as e:
        return None, e.read().decode()[:200]


def api(base: str, method: str, path: str, token: str, body: dict | None = None) -> tuple[int, object]:
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw[:300]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    args = parser.parse_args()
    base = args.backend.rstrip("/")

    print(f"Backend: {base}\n")
    token, err = login(base, *CLINIC_ADMIN)
    if not token:
        print(f"FAIL login clinic admin: {err}")
        return 1

    _, me = api(base, "GET", "/auth/me", token)
    clinic_id = me.get("clinic_id")
    print(f"OK   login clinic_admin role={me.get('role')} clinic_id={clinic_id} name={me.get('clinic_name')}")

    status, payload = api(
        base,
        "POST",
        "/clinical/clinics",
        token,
        {"name": "Forbidden Clinic", "city": "Conakry"},
    )
    ok = status == 403
    print(f"{'OK' if ok else 'FAIL'}  POST /clinical/clinics -> {status} {payload if not ok else '(forbidden as expected)'}")

    other_clinic = 2 if clinic_id == 1 else 1
    status, payload = api(
        base,
        "POST",
        "/clinical/staff",
        token,
        {
            "email": f"rbac.crossclinic.{other_clinic}@sante-gn.test",
            "password": "CrossClinic1!",
            "role": "receptionist",
            "clinic_id": other_clinic,
        },
    )
    ok = status == 403
    print(f"{'OK' if ok else 'FAIL'}  staff for other clinic_id={other_clinic} -> {status}")

    status, payload = api(
        base,
        "POST",
        "/clinical/staff",
        token,
        {
            "email": f"rbac.ownclinic.{clinic_id}@sante-gn.test",
            "password": "OwnClinic1!",
            "role": "receptionist",
            "clinic_id": clinic_id,
        },
    )
    ok = status in (201, 409)
    print(f"{'OK' if ok else 'FAIL'}  staff for own clinic_id={clinic_id} -> {status} {payload if not ok else ''}")

    status, _ = api(base, "GET", f"/platform/users", token)
    ok = status == 403
    print(f"{'OK' if ok else 'FAIL'}  GET /platform/users -> {status} (expect 403)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
