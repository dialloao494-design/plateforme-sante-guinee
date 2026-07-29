#!/usr/bin/env python3
"""Pre-restore validation + optional ephemeral restore drill gate (Wave 5)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.backup_security import pre_restore_validation  # noqa: E402
from services.recovery_security_service import validate_recovery_scenarios  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate backup before restore")
    parser.add_argument("backup", type=Path, help="Plain .sql.gz or .enc backup")
    parser.add_argument(
        "--require-encryption",
        action="store_true",
        help="Refuse plaintext backups",
    )
    parser.add_argument(
        "--scenarios",
        action="store_true",
        help="Run full Wave 5 recovery scenario matrix",
    )
    args = parser.parse_args()

    path = args.backup
    encrypted = path.name.endswith(".enc")
    if args.scenarios:
        report = validate_recovery_scenarios(
            plain_backup=None if encrypted else path,
            encrypted_backup=path if encrypted else None,
            require_encryption=args.require_encryption,
        )
        print(json.dumps(report, indent=2, default=str))
        return 0 if report.get("ok") else 1

    report = pre_restore_validation(path, require_encryption=args.require_encryption)
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
