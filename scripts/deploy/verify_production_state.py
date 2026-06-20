#!/usr/bin/env python3
"""Verify production deployment state for clinical modules."""

from __future__ import annotations

import re
import sys

import httpx

BASE = "https://web-production-ad6a36.up.railway.app"
FE = "https://frontend-seven-rust-94.vercel.app"
FE_LATEST = "https://frontend-9whoakkqk-dialloao494-designs-projects.vercel.app"


def main() -> int:
    client = httpx.Client(timeout=30.0, follow_redirects=True)
    print("=== BACKEND (Railway) ===")
    for path in ("/health", "/health/ready", "/openapi.json"):
        r = client.get(BASE + path)
        print(f"{path}: {r.status_code}")
        if path == "/health":
            print("  body:", r.text[:200])

    # Auth + module API probes
    login = client.post(
        BASE + "/auth/login-json",
        json={"email": "platform.admin@sante-gn.test", "password": "PlatformAdmin1!"},
    )
    print("login:", login.status_code)
    token = login.json().get("access_token") if login.status_code == 200 else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    api_routes = [
        "/clinical/immunization/dashboard",
        "/clinical/nursing-care/dashboard",
        "/clinical/hospitalization/dashboard",
        "/clinical/nutrition/dashboard",
    ]
    for path in api_routes:
        r = client.get(BASE + path, headers=headers)
        print(f"API {path}: {r.status_code}")

    print("\n=== FRONTEND (Vercel) ===")
    for fe_url in (FE, FE_LATEST):
        print(f"\n-- {fe_url} --")
        r = client.get(fe_url + "/")
        scripts = re.findall(r'src="(/assets/[^"]+\.js)"', r.text)
        print("index:", r.status_code, "scripts:", len(scripts))
        bundle = ""
        for s in scripts:
            if "clinical-pages" in s or "index-" in s:
                bundle += client.get(fe_url + s).text
        markers = [
            "clinical/pev",
            "clinical/nursing-care",
            "clinical/hospitalization",
            "clinical/nutrition",
            "NursingCareDashboard",
        ]
        for m in markers:
            print(f"  bundle has {m!r}:", m in bundle)

        for path in (
            "/clinical/pev",
            "/clinical/hospitalization",
            "/clinical/nursing-care",
            "/clinical/nutrition",
        ):
            r2 = client.get(fe_url + path)
            print(f"  route {path}: {r2.status_code} final={r2.url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
