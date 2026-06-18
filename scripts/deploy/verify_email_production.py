#!/usr/bin/env python3
"""Non-interactive production email verification via Resend API + auth endpoints."""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
DEFAULT_INBOX = "dialloao494@gmail.com"


def wait_configured(base: str, timeout_s: int = 180) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = httpx.get(f"{base}/health/email", timeout=20)
            if r.status_code == 200:
                body = r.json()
                if body.get("configured"):
                    return body
        except Exception:
            pass
        time.sleep(5)
    raise TimeoutError("Email channel not configured after deploy")


def list_resend_emails(api_key: str, limit: int = 20) -> list[dict]:
    r = httpx.get(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"limit": limit},
        timeout=30,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Resend list failed {r.status_code}: {r.text[:200]}")
    data = r.json()
    return data.get("data") or []


def recent_subjects(emails: list[dict]) -> set[str]:
    return {str(e.get("subject") or "") for e in emails}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=BACKEND)
    parser.add_argument("--inbox", default=DEFAULT_INBOX)
    parser.add_argument("--resend-key", default=os.getenv("RESEND_API_KEY", ""))
    args = parser.parse_args()

    base = args.backend.rstrip("/")
    inbox = args.inbox.strip().lower()
    api_key = args.resend_key.strip()
    if not api_key:
        print("ERROR: set RESEND_API_KEY env or pass --resend-key")
        return 1

    print("=== Wait for Railway deploy (email configured) ===")
    status = wait_configured(base)
    print("OK:", status)

    before = list_resend_emails(api_key)
    before_subjects = recent_subjects(before)
    print(f"Resend emails before: {len(before)}")

    suffix = uuid.uuid4().hex[:8]
    test_email = inbox
    password = f"EmailTest{suffix}A1!"

    print("\n=== Signup verification email ===")
    reg = httpx.post(
        f"{base}/auth/register",
        json={"email": test_email, "password": password, "role": "patient"},
        timeout=45,
    )
    print("register:", reg.status_code, reg.text[:200])
    if reg.status_code == 409:
        print("Account exists — resend verification instead")
        rv = httpx.post(f"{base}/auth/resend-verification", json={"email": test_email}, timeout=30)
        print("resend-verification:", rv.status_code, rv.text)
        if rv.status_code != 200:
            return 1
    elif reg.status_code != 201:
        return 1

    time.sleep(3)

    print("\n=== Forgot password email ===")
    forgot = httpx.post(f"{base}/auth/forgot-password", json={"email": test_email}, timeout=30)
    print("forgot-password:", forgot.status_code, forgot.text)
    if forgot.status_code != 200:
        return 1

    time.sleep(3)

    print("\n=== Verify via Resend API (delivery) ===")
    after = list_resend_emails(api_key)
    new_emails = [e for e in after if str(e.get("subject") or "") not in before_subjects]
    subjects = [e.get("subject") for e in new_emails]
    print("New emails:", len(new_emails))
    for e in new_emails[:5]:
        print(f"  - {e.get('subject')} -> {e.get('to')} status={e.get('last_event')}")

    verify_ok = any("Confirmez" in s or "confirm" in s.lower() for s in subjects if s)
    reset_ok = any("Réinitialisation" in s or "reset" in s.lower() for s in subjects if s)

    print("\n=== Results ===")
    print("signup verification sent:", verify_ok)
    print("forgot-password sent:", reset_ok)

    if verify_ok and reset_ok:
        print("PASS: both email types delivered via Resend")
        return 0
    print("FAIL: missing expected emails in Resend")
    return 1


if __name__ == "__main__":
    sys.exit(main())
