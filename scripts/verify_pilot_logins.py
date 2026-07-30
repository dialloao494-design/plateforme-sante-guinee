#!/usr/bin/env python3
"""
Verify pilot demo logins against a running API (default http://127.0.0.1:8000).

Usage:
  python scripts/verify_pilot_logins.py
  python scripts/verify_pilot_logins.py http://127.0.0.1:8080
"""
from __future__ import annotations
import os

import json
import sys
import urllib.error
import urllib.request

ACCOUNTS = [
    ("dr.amu@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", "")),
    ("dr.souleimane@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", "")),
    ("dr.fatou@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", "")),
    ("dr.mamady@example.com", os.environ.get("PILOT_DOCTOR_PASSWORD", "")),
    ("test.patient@example.com", os.environ.get("PILOT_PATIENT_PASSWORD", "")),
]


def post_json(url: str, payload: dict) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(err_body)
        except json.JSONDecodeError:
            detail = err_body
        return e.code, detail


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    url = f"{base}/auth/login-json"
    failed = 0
    for email, password in ACCOUNTS:
        code, body = post_json(url, {"email": email, "password": password})
        if code != 200 or not isinstance(body, dict) or not body.get("access_token"):
            print(f"FAIL {email} HTTP {code} {body}")
            failed += 1
        else:
            print(f"OK   {email} (token len={len(body['access_token'])})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
