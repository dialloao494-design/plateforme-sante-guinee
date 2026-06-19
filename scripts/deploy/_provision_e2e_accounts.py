"""Provision stable Clinique Alpha E2E accounts via production API (idempotent)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://web-production-ad6a36.up.railway.app"
ADMIN_EMAIL = "clinic.admin.a@sante-gn.test"
ADMIN_PASSWORD = "ClinicAdminA1!"
CLINIC_NAME = "Clinique Alpha Conakry"

# Stable credentials for end-to-end workflow (Clinique Alpha, clinic_id=1).
STAFF = [
    ("clinic_admin", "clinic.admin.a@sante-gn.test", "ClinicAdminA1!", "/clinical/admin"),
    ("receptionist", "reception.demo@sante-gn.test", "ReceptionDemo1!", "/clinical/reception"),
    ("doctor", "doctor.demo@sante-gn.test", "DoctorDemo1!", "/clinical/doctor"),
    ("lab_technician", "lab.demo@sante-gn.test", "LabDemo1!", "/clinical/lab"),
    ("pharmacist", "pharmacy.demo@sante-gn.test", "PharmaDemo1!", "/clinical/pharmacy"),
    ("cashier", "cashier.demo@sante-gn.test", "CashierDemo1!", "/clinical/reception"),
]

API_CHECKS = {
    "clinic_admin": [("GET", "/clinical/operations/summary"), ("GET", "/clinical/staff")],
    "receptionist": [("GET", "/clinical/reception/queue"), ("GET", "/clinical/workflow/queue/reception")],
    "doctor": [("GET", "/clinical/doctor/queue"), ("GET", "/clinical/workflow/queue/doctor")],
    "lab_technician": [("GET", "/clinical/lab/orders")],
    "pharmacist": [("GET", "/clinical/pharmacy/orders")],
    "cashier": [("GET", "/clinical/billing/charges/pending"), ("GET", "/clinical/reception/queue")],
}


def request(method: str, path: str, *, token: str | None = None, body: dict | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw[:300]
        return e.code, payload


def login(email: str, password: str) -> str | None:
    login_data = urllib.parse.urlencode({"username": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{BASE}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["access_token"]
    except urllib.error.HTTPError:
        return None


def main() -> int:
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin_token:
        print("FAIL: cannot login clinic admin")
        return 1

    _, me = request("GET", "/auth/me", token=admin_token)
    clinic_id = me.get("clinic_id")
    print(f"Admin OK — clinic_id={clinic_id} ({me.get('clinic_name')})\n")

    for role, email, password, _dashboard in STAFF:
        if role == "clinic_admin":
            continue
        status, payload = request(
            "POST",
            "/clinical/staff",
            token=admin_token,
            body={"email": email, "password": password, "role": role, "clinic_id": clinic_id},
        )
        if status == 201:
            print(f"CREATED {role:16} {email}")
        elif status in (409, 422, 400):
            print(f"EXISTS  {role:16} {email} ({status})")
        else:
            print(f"FAIL    {role:16} {email} HTTP {status} {payload}")

    print("\n=== Login + API verification ===\n")
    all_ok = True
    for role, email, password, dashboard in STAFF:
        token = login(email, password)
        if not token:
            print(f"LOGIN FAIL  {email}")
            all_ok = False
            continue
        _, profile = request("GET", "/auth/me", token=token)
        role_ok = profile.get("role") == role
        clinic_ok = profile.get("clinic_id") == clinic_id
        checks = API_CHECKS.get(role, [])
        api_ok = True
        api_detail = []
        for method, path in checks:
            params = ""
            if path == "/clinical/staff" and clinic_id:
                path = f"{path}?clinic_id={clinic_id}"
            status, _ = request(method, path, token=token)
            api_detail.append(f"{path}:{status}")
            if status >= 400:
                api_ok = False
        mark = "OK" if role_ok and clinic_ok and api_ok and token else "FAIL"
        if mark == "FAIL":
            all_ok = False
        print(
            f"{mark:4} {role:16} {email:35} dashboard={dashboard} "
            f"clinic_id={profile.get('clinic_id')} apis=[{', '.join(api_detail)}]"
        )

    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
