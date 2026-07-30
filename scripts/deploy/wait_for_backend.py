#!/usr/bin/env python3
"""Wait until production backend responds healthy (after Railway auto-deploy or CLI deploy)."""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx


def _print_blocker_hint(*, saw_502: bool, saw_timeout: bool) -> None:
    token = (os.getenv("RAILWAY_TOKEN") or "").strip()
    svc = (os.getenv("SVC_ID") or os.getenv("RAILWAY_SERVICE_ID") or "").strip()
    print("", file=sys.stderr)
    print("=" * 72, file=sys.stderr)
    print("RAILWAY RECOVERY BLOCKER", file=sys.stderr)
    print("=" * 72, file=sys.stderr)
    if not token or not svc:
        print(
            "Classification: missing GitHub secret / Railway permission "
            "(RAILWAY_TOKEN and/or RAILWAY_SERVICE_ID empty).",
            file=sys.stderr,
        )
        print(
            "Actions skipped CLI deploy and waited for GitHub auto-deploy only.",
            file=sys.stderr,
        )
    if saw_502:
        print(
            "Live signal: HTTP 502 Application failed to respond "
            "(Railway edge — process not serving / crashed / not deployed).",
            file=sys.stderr,
        )
    if saw_timeout:
        print("Live signal: connection timeout to backend URL.", file=sys.stderr)
    print(
        "Exact manual steps: docs/RAILWAY_502_MANUAL_RECOVERY.md",
        file=sys.stderr,
    )
    print(
        "Provide RAILWAY_TOKEN + RAILWAY_SERVICE_ID (project token) OR "
        "Redeploy from Railway dashboard and paste deploy logs.",
        file=sys.stderr,
    )
    print("=" * 72, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=600, help="Max seconds to wait")
    parser.add_argument("--interval", type=int, default=10, help="Poll interval seconds")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    deadline = time.time() + args.timeout
    attempt = 0
    saw_502 = False
    saw_timeout = False
    while time.time() < deadline:
        attempt += 1
        try:
            h = httpx.get(f"{base}/health", timeout=20)
            r = httpx.get(f"{base}/health/ready", timeout=20)
            if h.status_code == 502 or r.status_code == 502:
                saw_502 = True
            if h.status_code == 200 and r.status_code == 200 and r.json().get("status") == "ready":
                print(f"[OK] Backend ready after {attempt} attempt(s): {base}")
                return 0
            print(
                f"[wait] attempt={attempt} health={h.status_code} "
                f"ready={r.status_code} body={r.text[:80]}"
            )
        except Exception as exc:
            msg = str(exc).lower()
            if "timed out" in msg or "timeout" in msg:
                saw_timeout = True
            print(f"[wait] attempt={attempt} error={exc}")
        time.sleep(args.interval)
    print(f"[FAIL] Backend not ready within {args.timeout}s: {base}", file=sys.stderr)
    _print_blocker_hint(saw_502=saw_502, saw_timeout=saw_timeout)
    return 1


if __name__ == "__main__":
    sys.exit(main())
