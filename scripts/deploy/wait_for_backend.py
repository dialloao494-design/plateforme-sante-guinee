#!/usr/bin/env python3
"""Wait until production backend responds healthy (after Railway auto-deploy or CLI deploy)."""

from __future__ import annotations

import argparse
import sys
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Backend base URL")
    parser.add_argument("--timeout", type=int, default=600, help="Max seconds to wait")
    parser.add_argument("--interval", type=int, default=10, help="Poll interval seconds")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    deadline = time.time() + args.timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            h = httpx.get(f"{base}/health", timeout=20)
            r = httpx.get(f"{base}/health/ready", timeout=20)
            if h.status_code == 200 and r.status_code == 200 and r.json().get("status") == "ready":
                print(f"[OK] Backend ready after {attempt} attempt(s): {base}")
                return 0
            print(f"[wait] attempt={attempt} health={h.status_code} ready={r.status_code} body={r.text[:80]}")
        except Exception as exc:
            print(f"[wait] attempt={attempt} error={exc}")
        time.sleep(args.interval)
    print(f"[FAIL] Backend not ready within {args.timeout}s: {base}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
