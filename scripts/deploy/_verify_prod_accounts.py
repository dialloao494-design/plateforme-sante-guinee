"""Verify production demo account logins (read-only)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://web-production-ad6a36.up.railway.app"

ACCOUNTS = [
    ("platform.admin@sante-gn.test", "PlatformAdmin1!", "platform_admin"),
    ("clinic.admin.a@sante-gn.test", "ClinicAdminA1!", "clinic_admin"),
    ("clinic.admin.b@sante-gn.test", "ClinicAdminB1!", "clinic_admin"),
    ("doctor.demo@sante-gn.test", "DoctorDemo1!", "doctor"),
    ("reception.demo@sante-gn.test", "ReceptionDemo1!", "receptionist"),
    ("reception.beta@sante-gn.test", "ReceptionBeta1!", "receptionist"),
    ("audit.recv.9a4b5d83@sante-gn.test", "AuditRecv1!", "receptionist"),
    ("audit.doc.9a4b5d83@sante-gn.test", "AuditDoctor1!", "doctor"),
    ("audit.lab.9a4b5d83@sante-gn.test", "AuditLab1!", "lab_technician"),
    ("audit.pharma.9a4b5d83@sante-gn.test", "AuditPharma1!", "pharmacist"),
    ("audit.nutri.9a4b5d83@sante-gn.test", "AuditNutri1!", "nutritionist"),
    ("audit.midwife.9a4b5d83@sante-gn.test", "AuditMidwife1!", "midwife"),
    ("cashier@pilot.local", "CashierPilot1!", "cashier"),
    ("lab@pilot.local", "LabPilot123!", "lab_technician"),
    ("pharmacy@pilot.local", "PharmacyPilot1!", "pharmacist"),
    ("reception@pilot.local", "ReceptionPilot1!", "receptionist"),
    ("dr.pilot@pilot.local", "DoctorPilot1!", "doctor"),
]


def login(email: str, password: str) -> tuple[int, dict | str]:
    login_data = urllib.parse.urlencode({"username": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{BASE}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def me(token: str) -> dict:
    req = urllib.request.Request(
        f"{BASE}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def main() -> int:
    print(f"API: {BASE}\n")
    ok = 0
    for email, password, expected in ACCOUNTS:
        status, payload = login(email, password)
        if status != 200 or not isinstance(payload, dict):
            print(f"FAIL  {email:45} HTTP {status} {payload}")
            continue
        profile = me(payload["access_token"])
        role = profile.get("role")
        mark = "OK" if role == expected else "WARN"
        if mark == "OK":
            ok += 1
        print(
            f"{mark:4}  {email:45} role={role:16} clinic_id={profile.get('clinic_id')} "
            f"clinic={profile.get('clinic_name') or '-'}"
        )
    print(f"\n{ok}/{len(ACCOUNTS)} logins OK with expected role")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
