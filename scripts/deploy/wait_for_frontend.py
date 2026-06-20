#!/usr/bin/env python3
"""Wait until production frontend responds (after Vercel auto-deploy or CLI deploy)."""

from __future__ import annotations

import argparse
import re
import sys
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Frontend base URL")
    parser.add_argument("--timeout", type=int, default=600, help="Max seconds to wait")
    parser.add_argument("--interval", type=int, default=10, help="Poll interval seconds")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    deadline = time.time() + args.timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            r = httpx.get(base + "/", timeout=30, follow_redirects=True)
            if r.status_code == 200 and "assets/" in r.text:
                scripts = re.findall(r'src="(/assets/[^"]+\.js)"', r.text)
                if scripts:
                    print(f"[OK] Frontend ready after {attempt} attempt(s): {base}")
                    return 0
            print(f"[wait] attempt={attempt} http={r.status_code} has_assets={'assets/' in r.text}")
        except Exception as exc:
            print(f"[wait] attempt={attempt} error={exc}")
        time.sleep(args.interval)
    print(f"[FAIL] Frontend not ready within {args.timeout}s: {base}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
