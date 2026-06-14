"""Validate daily database backups for production readiness."""

from __future__ import annotations

import gzip
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


def validate_backup_directory(
    backup_dir: str | Path,
    *,
    max_age_hours: int = 26,
    pattern: str = "sante_*.sql.gz",
) -> dict[str, Any]:
    """Check that a recent, readable backup exists in backup_dir."""
    root = Path(backup_dir)
    result: dict[str, Any] = {
        "status": "fail",
        "backup_dir": str(root.resolve()),
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "latest_backup": None,
        "age_hours": None,
        "gzip_valid": False,
        "message": "",
    }

    if not root.is_dir():
        result["message"] = f"Backup directory not found: {root}"
        return result

    candidates = sorted(root.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        verify_candidates = sorted(root.glob("verify_*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidates = verify_candidates

    if not candidates:
        result["message"] = "No backup files found"
        return result

    latest = candidates[0]
    mtime = datetime.utcfromtimestamp(latest.stat().st_mtime)
    age = datetime.utcnow() - mtime
    age_hours = age.total_seconds() / 3600.0

    gzip_valid = False
    try:
        with gzip.open(latest, "rb") as fh:
            header = fh.read(256)
            gzip_valid = len(header) > 0 and (
                header.startswith(b"--") or header.startswith(b"PGDMP") or b"PostgreSQL" in header
            )
    except OSError:
        gzip_valid = False

    result["latest_backup"] = latest.name
    result["age_hours"] = round(age_hours, 2)
    result["gzip_valid"] = gzip_valid

    if age_hours > max_age_hours:
        result["message"] = f"Latest backup is too old ({age_hours:.1f}h > {max_age_hours}h)"
        return result

    if not gzip_valid:
        result["message"] = "Latest backup failed gzip/SQL header validation"
        return result

    result["status"] = "ok"
    result["message"] = "Daily backup validation passed"
    return result


def default_backup_dir() -> Path:
    env = os.getenv("BACKUP_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "backups"
