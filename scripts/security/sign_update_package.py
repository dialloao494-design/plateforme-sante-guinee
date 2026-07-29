#!/usr/bin/env python3
"""Sign an update package with CLINIC_NODE_UPDATE_SECRET (no JWT fallback)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.update_security import UpdateSecurityError, write_signed_package  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign Clinic Node update package")
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("--version", default=None)
    parser.add_argument("--backup-required", action="store_true", default=True)
    args = parser.parse_args()

    pkg = args.package_dir
    manifest = pkg / "manifest.json"
    if manifest.is_file():
        claims = json.loads(manifest.read_text(encoding="utf-8"))
    else:
        claims = {
            "version": args.version or "0.0.0",
            "backup_required": True,
        }
    if args.version:
        claims["version"] = args.version
    claims["backup_required"] = bool(claims.get("backup_required", True))

    try:
        package = write_signed_package(pkg, claims)
    except UpdateSecurityError as exc:
        print(f"SIGN_FAIL {exc}", file=sys.stderr)
        return 2
    print(f"SIGNED {package.version} {package.signature[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
