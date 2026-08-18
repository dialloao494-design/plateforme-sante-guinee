#!/usr/bin/env python3
"""Validate a PostgreSQL backup and optionally prove an isolated restore.

The restore target must be a distinct database whose name ends in
``_restore_verify``. The script never accepts a live/source database as its
target and never drops a database unless ``--replace-verification-database`` is
explicitly supplied.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse, urlunparse


MIN_BACKUP_BYTES = 200
VERIFY_SUFFIX = "_restore_verify"
CRITICAL_TABLES = ("clinics", "users", "patients", "invoices", "audit_logs")


def database_name(database_url: str) -> str:
    return urlparse(database_url).path.lstrip("/")


def maintenance_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    return urlunparse(parsed._replace(path="/postgres"))


def validate_isolated_target(source_url: str | None, verification_url: str) -> str:
    target_name = database_name(verification_url)
    source_name = database_name(source_url) if source_url else None
    if target_name in {"postgres", "template0", "template1"}:
        raise ValueError("System databases cannot be restore targets")
    if not target_name.endswith(VERIFY_SUFFIX):
        raise ValueError(f"Verification database must end with {VERIFY_SUFFIX}")
    if source_name and source_name == target_name:
        raise ValueError("Verification database must differ from the source database")
    return target_name


def inspect_backup(path: Path, *, rpo_target_minutes: int) -> dict:
    if not path.is_file():
        raise ValueError(f"Backup not found: {path}")
    compressed_bytes = path.stat().st_size
    if compressed_bytes < MIN_BACKUP_BYTES:
        raise ValueError(f"Backup is too small ({compressed_bytes} bytes)")

    digest = hashlib.sha256()
    with path.open("rb") as raw:
        for chunk in iter(lambda: raw.read(1024 * 1024), b""):
            digest.update(chunk)

    expanded_bytes = 0
    prefix = b""
    try:
        with gzip.open(path, "rb") as stream:
            while chunk := stream.read(1024 * 1024):
                expanded_bytes += len(chunk)
                if len(prefix) < 64 * 1024:
                    prefix += chunk[: 64 * 1024 - len(prefix)]
    except (OSError, EOFError) as error:
        raise ValueError(f"Backup gzip integrity failed: {error}") from error

    if b"PostgreSQL database dump" not in prefix and b"CREATE TABLE" not in prefix:
        raise ValueError("Backup does not contain a recognizable PostgreSQL SQL dump")

    now = time.time()
    rpo_seconds = max(0, int(now - path.stat().st_mtime))
    return {
        "path": str(path.resolve()),
        "sha256": digest.hexdigest(),
        "compressed_bytes": compressed_bytes,
        "expanded_bytes": expanded_bytes,
        "backup_mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "rpo_seconds": rpo_seconds,
        "rpo_target_seconds": rpo_target_minutes * 60,
        "rpo_met": rpo_seconds <= rpo_target_minutes * 60,
        "gzip_integrity": True,
        "sql_signature": True,
    }


def _connect(url: str, *, autocommit: bool = False):
    import psycopg2

    connection = psycopg2.connect(url)
    connection.autocommit = autocommit
    return connection


def _database_exists(maintenance_database_url: str, name: str) -> bool:
    with _connect(maintenance_database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            return cursor.fetchone() is not None


def _drop_database(maintenance_database_url: str, name: str) -> None:
    from psycopg2 import sql

    with _connect(maintenance_database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            cursor.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def _create_database(maintenance_database_url: str, name: str) -> None:
    from psycopg2 import sql

    with _connect(maintenance_database_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def restore_sql(backup: Path, verification_url: str) -> None:
    psql = shutil.which("psql")
    if not psql:
        raise RuntimeError("psql is required for an executable restore drill")
    parsed = urlparse(verification_url)
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = unquote(parsed.password)
    command = [
        psql,
        "--host", parsed.hostname or "localhost",
        "--port", str(parsed.port or 5432),
        "--username", unquote(parsed.username or "postgres"),
        "--dbname", database_name(verification_url),
        "--set", "ON_ERROR_STOP=1",
        "--quiet",
    ]
    with gzip.open(backup, "rb") as sql_stream:
        result = subprocess.run(
            command,
            stdin=sql_stream,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace")[-2000:]
        raise RuntimeError(f"Restore failed with psql exit {result.returncode}: {detail}")


def run_integrity_checks(verification_url: str) -> dict:
    with _connect(verification_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = {row[0] for row in cursor.fetchall()}
            if "alembic_version" not in tables:
                raise RuntimeError("Restored database is missing alembic_version")
            cursor.execute("SELECT version_num FROM alembic_version")
            migration_heads = sorted(row[0] for row in cursor.fetchall())
            if not migration_heads:
                raise RuntimeError("Restored database has no Alembic migration head")

            row_counts = {}
            from psycopg2 import sql

            for table in CRITICAL_TABLES:
                if table in tables:
                    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                    row_counts[table] = cursor.fetchone()[0]

            orphan_checks = {}
            if {"patients", "clinics"}.issubset(tables):
                cursor.execute(
                    "SELECT COUNT(*) FROM patients p LEFT JOIN clinics c ON c.id=p.clinic_id "
                    "WHERE p.clinic_id IS NOT NULL AND c.id IS NULL"
                )
                orphan_checks["patients_without_clinic"] = cursor.fetchone()[0]
            if orphan_checks and any(orphan_checks.values()):
                raise RuntimeError(f"Referential integrity check failed: {orphan_checks}")

    return {
        "table_count": len(tables),
        "migration_heads": migration_heads,
        "critical_row_counts": row_counts,
        "orphan_checks": orphan_checks,
        "integrity_ok": True,
    }


def execute_drill(args: argparse.Namespace, artifact: dict) -> dict:
    target_name = validate_isolated_target(args.source_database_url, args.verification_database_url)
    admin_url = maintenance_url(args.verification_database_url)
    existed = _database_exists(admin_url, target_name)
    if existed and not args.replace_verification_database:
        raise RuntimeError(
            f"Verification database {target_name} already exists; use --replace-verification-database explicitly"
        )
    if existed:
        _drop_database(admin_url, target_name)

    started = time.monotonic()
    _create_database(admin_url, target_name)
    try:
        restore_sql(args.backup, args.verification_database_url)
        integrity = run_integrity_checks(args.verification_database_url)
        rto_seconds = round(time.monotonic() - started, 3)
        return {
            "executed": True,
            "verification_database": target_name,
            "rto_seconds": rto_seconds,
            "rto_target_seconds": args.rto_target_minutes * 60,
            "rto_met": rto_seconds <= args.rto_target_minutes * 60,
            **integrity,
        }
    finally:
        if not args.keep_verification_database and _database_exists(admin_url, target_name):
            _drop_database(admin_url, target_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--source-database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--verification-database-url")
    parser.add_argument("--replace-verification-database", action="store_true")
    parser.add_argument("--keep-verification-database", action="store_true")
    parser.add_argument("--rpo-target-minutes", type=int, default=24 * 60)
    parser.add_argument("--rto-target-minutes", type=int, default=60)
    parser.add_argument("--evidence", type=Path, default=Path("evidence/backup/latest-restore-drill.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = {
        "format": "sante-guinee-backup-restore-evidence-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact": None,
        "restore": {"executed": False},
        "ok": False,
    }
    try:
        report["artifact"] = inspect_backup(args.backup, rpo_target_minutes=args.rpo_target_minutes)
        if args.verification_database_url:
            report["restore"] = execute_drill(args, report["artifact"])
        report["ok"] = bool(
            report["artifact"]["rpo_met"]
            and (not args.verification_database_url or report["restore"].get("integrity_ok"))
            and (not args.verification_database_url or report["restore"].get("rto_met"))
        )
    except Exception as error:
        report["error"] = str(error)

    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
