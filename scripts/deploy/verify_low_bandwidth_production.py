#!/usr/bin/env python3
"""Verify low-bandwidth optimizations on production (cache headers + API health)."""

from __future__ import annotations

import sys

import httpx

FRONTEND = "https://frontend-seven-rust-94.vercel.app"
BACKEND = "https://web-production-ad6a36.up.railway.app"


def main() -> int:
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        print(f"[{'OK' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not cond:
            ok = False

    r = httpx.get(f"{BACKEND}/health", timeout=30)
    check("Backend health", r.status_code == 200)
    check("Health Cache-Control", "max-age" in r.headers.get("cache-control", "").lower(), r.headers.get("cache-control"))

    r = httpx.get(f"{BACKEND}/clinical/immunization/schedule", timeout=30, headers={"Authorization": "Bearer invalid"})
    # May 401 without auth — still check if route exists
    check("Immunization schedule route", r.status_code in (200, 401, 403))

    r = httpx.get(FRONTEND, timeout=45, follow_redirects=True)
    check("Frontend loads", r.status_code == 200)
    html = r.text
    check("No Google Fonts in HTML", "fonts.googleapis.com" not in html)
    check("Viewport meta", "viewport" in html.lower())

    # Find a hashed asset from built index if present
    import re

    asset_match = re.search(r'/assets/[^"\']+\.js', html)
    if asset_match:
        asset_url = FRONTEND + asset_match.group(0)
        ar = httpx.head(asset_url, timeout=30, follow_redirects=True)
        cc = ar.headers.get("cache-control", "")
        check("JS asset immutable cache", "immutable" in cc.lower() or "max-age" in cc.lower(), cc[:80])
    else:
        print("[WARN] No /assets/*.js in index — deploy may still be propagating")

    print(f"\nFrontend: {FRONTEND}")
    print(f"Backend: {BACKEND}")
    print("\nManual 3G test: Chrome DevTools → Network → Slow 3G → load /login then /clinical/reception")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
