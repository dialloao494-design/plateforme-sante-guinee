"""Clinic Node backup, verification, restore, and retention."""

from __future__ import annotations

import gzip
import hashlib
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from models.clinic_node_ops import ClinicNodeBackupRecord

logger = logging.getLogger(__name__)

MIN_VALID_BYTES = 200
RETENTION_DAYS = int(os.getenv("CLINIC_NODE_BACKUP_RETENTION_DAYS", "30"))
KEEP_MIN = int(os.getenv("CLINIC_NODE_BACKUP_KEEP_MIN", "7"))


def clinic_data_dir() -> Path:
    data_dir = Path(os.getenv("CLINIC_DATA_DIR") or "/clinic-data")
    if not data_dir.exists():
        data_dir = Path("deploy/clinic-node/data")
    return data_dir


def backups_dir() -> Path:
    target = clinic_data_dir() / "backups"
    target.mkdir(parents=True, exist_ok=True)
    return target


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_backup_file(path: Path) -> dict:
    """Validate gzip integrity and minimum size."""
    if not path.exists():
        return {"ok": False, "error": "missing", "path": str(path)}
    size = path.stat().st_size
    if size < MIN_VALID_BYTES:
        return {"ok": False, "error": "undersized", "bytes": size, "path": str(path)}
    try:
        with gzip.open(path, "rb") as gz:
            # Read first chunk to force CRC check on that member.
            chunk = gz.read(65536)
            if not chunk:
                return {"ok": False, "error": "empty_gzip", "bytes": size, "path": str(path)}
            # Drain remainder for full CRC
            while gz.read(1024 * 1024):
                pass
    except Exception as exc:
        return {"ok": False, "error": f"gzip_invalid:{exc}", "bytes": size, "path": str(path)}
    digest = sha256_file(path)
    return {"ok": True, "bytes": size, "sha256": digest, "path": str(path)}


def run_local_backup(db: Session | None = None, clinic_id: int | None = None) -> dict:
    """Create a local pg_dump backup, verify integrity, record metadata, prune old."""
    target = backups_dir()
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outfile = target / f"clinic-node-{stamp}.sql.gz"
    database_url = os.getenv("DATABASE_URL") or ""

    def _finalize(path: Path, method: str) -> dict:
        verified = verify_backup_file(path)
        if not verified.get("ok"):
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
            return {
                "ok": False,
                "path": "",
                "bytes": 0,
                "created_at": stamp,
                "method": method,
                "error": verified.get("error"),
            }
        record = {
            "ok": True,
            "path": str(path),
            "bytes": verified["bytes"],
            "sha256": verified["sha256"],
            "verified": True,
            "created_at": stamp,
            "method": method,
        }
        if db is not None:
            db.add(
                ClinicNodeBackupRecord(
                    clinic_id=clinic_id,
                    path=str(path),
                    sha256=verified["sha256"],
                    bytes=verified["bytes"],
                    verified=True,
                    method=method,
                )
            )
            db.commit()
        prune_old_backups(db=db)
        return record

    def _run_pipe(cmd: str) -> None:
        subprocess.run(
            ["bash", "-lc", f"set -euo pipefail; {cmd}"],
            check=True,
            capture_output=True,
            text=True,
        )

    if database_url.startswith("postgresql"):
        try:
            _run_pipe(
                f"pg_dump --dbname={database_url!r} --no-owner --no-acl | gzip -c > {str(outfile)!r}"
            )
            result = _finalize(outfile, "pg_dump")
            if result["ok"]:
                return result
        except Exception as exc:
            logger.error("pg_dump via DATABASE_URL failed: %s", exc)

        try:
            user = os.getenv("POSTGRES_USER") or "sante"
            password = os.getenv("POSTGRES_PASSWORD") or ""
            dbname = os.getenv("POSTGRES_DB") or "sante"
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = password
            subprocess.run(
                [
                    "bash",
                    "-lc",
                    "set -euo pipefail; "
                    f"pg_dump -h '127.0.0.1' -U {user!r} -d {dbname!r} --no-owner --no-acl "
                    f"| gzip -c > {str(outfile)!r}",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            result = _finalize(outfile, "pg_dump_env")
            if result["ok"]:
                return result
        except Exception as exc:
            logger.error("pg_dump via POSTGRES_* env failed: %s", exc)

        try:
            _run_pipe(
                "sudo docker exec clinic-node-db-1 pg_dump -U sante --no-owner --no-acl sante "
                f"| gzip -c > {str(outfile)!r}"
            )
            result = _finalize(outfile, "pg_dump_docker")
            if result["ok"]:
                return result
        except Exception as exc:
            logger.error("pg_dump docker backup failed: %s", exc)

    return {
        "ok": False,
        "path": "",
        "bytes": 0,
        "created_at": stamp,
        "method": "failed",
        "error": "pg_dump unavailable",
    }


def prune_old_backups(db: Session | None = None) -> dict:
    files = sorted(backups_dir().glob("clinic-node-*.sql.gz"), key=lambda p: p.stat().st_mtime)
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    removed = []
    # Keep newest KEEP_MIN always
    keep = set(files[-KEEP_MIN:]) if len(files) > KEEP_MIN else set(files)
    for path in files:
        if path in keep:
            continue
        mtime = datetime.utcfromtimestamp(path.stat().st_mtime)
        if mtime < cutoff:
            try:
                path.unlink()
                removed.append(str(path))
            except OSError:
                pass
    return {"removed": removed, "kept": len(files) - len(removed)}


def restore_backup(
    backup_path: str | Path,
    *,
    target_database_url: str | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Restore a verified .sql.gz into Postgres.
    For Clinic Node appliance, defaults to DATABASE_URL.
    """
    path = Path(backup_path)
    verified = verify_backup_file(path)
    if not verified.get("ok"):
        return {"ok": False, "error": verified.get("error"), "path": str(path)}

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "path": str(path),
            "sha256": verified["sha256"],
            "bytes": verified["bytes"],
        }

    database_url = target_database_url or os.getenv("DATABASE_URL") or ""
    if not database_url.startswith("postgresql"):
        return {"ok": False, "error": "DATABASE_URL required for restore"}

    # Safety: require explicit confirm env for destructive restore via API layer.
    cmd = (
        "set -euo pipefail; "
        f"gzip -dc {str(path)!r} | psql --dbname={database_url!r} -v ON_ERROR_STOP=1"
    )
    try:
        subprocess.run(["bash", "-lc", cmd], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        logger.error("restore failed: %s", exc.stderr[-500:] if exc.stderr else exc)
        return {"ok": False, "error": "restore_failed", "detail": (exc.stderr or "")[-500:]}

    return {
        "ok": True,
        "path": str(path),
        "sha256": verified["sha256"],
        "bytes": verified["bytes"],
        "restored_at": datetime.utcnow().isoformat() + "Z",
    }
