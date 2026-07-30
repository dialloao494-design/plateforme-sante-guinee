#!/usr/bin/env python3
"""Encrypt a .sql.gz backup with Fernet + SHA-256 sidecar (Wave 5)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.backup_security import encrypt_backup_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Encrypt Santé Guinée SQL backup")
    parser.add_argument("src", type=Path, help="Path to .sql.gz backup")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output path (default: <src>.enc)",
    )
    args = parser.parse_args()
    try:
        artifact = encrypt_backup_file(args.src, args.out)
    except Exception as exc:
        print(f"ENCRYPT_FAIL {exc}", file=sys.stderr)
        return 1
    print(f"ENCRYPT_OK {artifact.path} sha256={artifact.sha256} bytes={artifact.bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
