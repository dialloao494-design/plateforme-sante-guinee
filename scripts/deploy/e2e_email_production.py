#!/usr/bin/env python3
"""Production E2E: signup verification, forgot-password, and reset-password email flows."""

from __future__ import annotations

import argparse
import sys
import uuid

import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify production email flows")
    parser.add_argument("--backend", default=BACKEND)
    parser.add_argument("--inbox", required=True, help="Real inbox email to receive messages")
    parser.add_argument("--password", default="EmailTest1!", help="Password for test account")
    args = parser.parse_args()

    base = args.backend.rstrip("/")
    suffix = uuid.uuid4().hex[:8]
    test_email = args.inbox.strip().lower()
    new_pass = f"Reset{suffix}A1!"

    print("=== 1. Email channel status ===")
    r = httpx.get(f"{base}/health/email", timeout=30)
    print(r.status_code, r.text)
    if r.status_code != 200 or not r.json().get("configured"):
        print("BLOCKER: SMTP/Resend not configured on Railway")
        return 1

    print("\n=== 2. Signup (verification email) ===")
    reg = httpx.post(
        f"{base}/auth/register",
        json={"email": test_email, "password": args.password, "role": "patient"},
        timeout=45,
    )
    print(reg.status_code, reg.text[:300])
    if reg.status_code not in (201, 409):
        print("FAIL: register")
        return 1
    print("CHECK INBOX: verification email with /verify-email?token=...")

    print("\n=== 3. Resend verification (if already registered) ===")
    resend = httpx.post(f"{base}/auth/resend-verification", json={"email": test_email}, timeout=30)
    print(resend.status_code, resend.text)

    print("\n=== 4. Forgot password ===")
    forgot = httpx.post(f"{base}/auth/forgot-password", json={"email": test_email}, timeout=30)
    print(forgot.status_code, forgot.text)
    if forgot.status_code != 200:
        print("FAIL: forgot-password")
        return 1
    print("CHECK INBOX: reset email with /reset-password?token=...")
    print("\nPaste reset token from email to complete step 5 manually:")
    token = input("reset token: ").strip()
    if not token:
        print("Skipped reset-password (no token pasted)")
        return 0

    print("\n=== 5. Reset password ===")
    reset = httpx.post(
        f"{base}/auth/reset-password",
        json={"token": token, "new_password": new_pass},
        timeout=30,
    )
    print(reset.status_code, reset.text)
    if reset.status_code != 200:
        print("FAIL: reset-password")
        return 1

    print("\n=== 6. Login with new password ===")
    login = httpx.post(
        f"{base}/auth/login-json",
        json={"email": test_email, "password": new_pass},
        timeout=30,
    )
    print(login.status_code, "token" if login.status_code == 200 and login.json().get("access_token") else login.text[:200])
    return 0 if login.status_code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
