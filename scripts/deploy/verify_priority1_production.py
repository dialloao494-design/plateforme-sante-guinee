#!/usr/bin/env python3
"""Verify Priority 1 modules on production (nutrition, PEV, auth reset, staff list)."""

from __future__ import annotations

import argparse
import sys
import uuid

import httpx

DEFAULT_BACKEND = "https://web-production-ad6a36.up.railway.app"
DEFAULT_FRONTEND = "https://plateforme-sante-guinee.vercel.app"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument("--frontend", default=DEFAULT_FRONTEND)
    args = parser.parse_args()
    base = args.backend.rstrip("/")
    fe = args.frontend.rstrip("/")
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        if cond:
            print(f"[OK] {label}" + (f" — {detail}" if detail else ""))
        else:
            ok = False
            print(f"[FAIL] {label}" + (f" — {detail}" if detail else ""), file=sys.stderr)

    try:
        r = httpx.get(f"{base}/health", timeout=30)
        check("Backend health", r.status_code == 200 and r.json().get("status") == "ok", str(r.status_code))

        r = httpx.post(f"{base}/auth/forgot-password", json={"email": "nobody@example.com"}, timeout=30)
        check("Forgot password endpoint", r.status_code == 200, str(r.status_code))

        r = httpx.get(f"{base}/clinical/immunization/schedule", timeout=30)
        check(
            "Immunization schedule (auth required)",
            r.status_code in (401, 403),
            f"expected 401/403 before deploy auth, got {r.status_code}",
        )

        r = httpx.get(f"{fe}/forgot-password", timeout=30, follow_redirects=True)
        check("Frontend forgot-password page", r.status_code == 200, fe + "/forgot-password")

        r = httpx.get(f"{fe}/reset-password", timeout=30, follow_redirects=True)
        check("Frontend reset-password page", r.status_code == 200, fe + "/reset-password")

        r = httpx.get(f"{fe}/clinical/nutrition", timeout=30, follow_redirects=True)
        check("Frontend nutrition route (SPA)", r.status_code == 200)

        r = httpx.get(f"{fe}/clinical/immunization", timeout=30, follow_redirects=True)
        check("Frontend immunization route (SPA)", r.status_code == 200)

        # Authenticated checks with staging E2E accounts (if seeded)
        login = httpx.post(
            f"{base}/auth/login-json",
            json={"email": "clinic.admin.a@sante-gn.test", "password": "ClinicAdminA1!"},
            timeout=30,
        )
        if login.status_code == 200:
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            me = httpx.get(f"{base}/auth/me", headers=headers, timeout=30).json()
            clinic_id = me.get("clinic_id")
            check("Clinic admin login", bool(clinic_id), f"clinic_id={clinic_id}")

            if clinic_id:
                r = httpx.get(
                    f"{base}/clinical/staff",
                    params={"clinic_id": clinic_id},
                    headers=headers,
                    timeout=30,
                )
                check("Staff list API", r.status_code == 200, f"count={len(r.json()) if r.status_code==200 else r.text[:80]}")

            r = httpx.get(f"{base}/clinical/immunization/schedule", headers=headers, timeout=30)
            check(
                "Immunization schedule (authenticated)",
                r.status_code == 200 and len(r.json()) >= 10,
                f"items={len(r.json()) if r.status_code==200 else 0}",
            )
        else:
            print("[WARN] Staging clinic admin not available — skip authenticated API checks")

        print("=== Priority 1 production verification complete ===")
        return 0 if ok else 1
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
