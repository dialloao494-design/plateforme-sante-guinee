#!/usr/bin/env python3
"""Daily backup validation — run from cron after backup-db.sh."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.backup_validation_service import default_backup_dir, validate_backup_directory


def main() -> int:
    result = validate_backup_directory(default_backup_dir())
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
