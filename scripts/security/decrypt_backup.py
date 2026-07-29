#!/usr/bin/env python3
"""Decrypt a Wave 5 .enc backup and verify gzip/SQL integrity."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.backup_security import decrypt_backup_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Decrypt Santé Guinée encrypted backup")
    parser.add_argument("src", type=Path, help="Path to .sql.gz.enc backup")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Output plaintext .sql.gz path",
    )
    args = parser.parse_args()
    try:
        artifact = decrypt_backup_file(args.src, args.out)
    except Exception as exc:
        print(f"DECRYPT_FAIL {exc}", file=sys.stderr)
        return 1
    print(f"DECRYPT_OK {artifact.path} sha256={artifact.sha256} bytes={artifact.bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
