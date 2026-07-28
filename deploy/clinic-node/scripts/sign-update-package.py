#!/usr/bin/env python3
"""Sign a Clinic Node update manifest with HMAC-SHA256."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: sign-update-package.py <package-dir>", file=sys.stderr)
        return 2
    pkg = Path(sys.argv[1])
    manifest = pkg / "manifest.json"
    secret = (os.getenv("CLINIC_NODE_UPDATE_SECRET") or os.getenv("JWT_SECRET") or "").encode()
    if not secret:
        print("CLINIC_NODE_UPDATE_SECRET or JWT_SECRET required", file=sys.stderr)
        return 2
    claims = json.loads(manifest.read_text(encoding="utf-8"))
    canon = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    sig = hmac.new(secret, canon, hashlib.sha256).hexdigest()
    (pkg / "manifest.sig").write_text(sig + "\n", encoding="utf-8")
    print("SIGNED", claims.get("version"), sig[:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
