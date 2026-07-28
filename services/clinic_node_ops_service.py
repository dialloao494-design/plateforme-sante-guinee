"""Clinic Node Phase 3–4 services: outbox sync, license, backup, heartbeat."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from models.clinic_node_ops import (
    ClinicNodeHeartbeat,
    ClinicNodeLicense,
    SyncConflict,
    SyncOutboxEvent,
)

logger = logging.getLogger(__name__)
SOFTWARE_VERSION = os.getenv("CLINIC_NODE_SOFTWARE_VERSION", "offline-v1.0.0")


def enqueue_outbox_event(
    db: Session,
    *,
    clinic_id: int,
    entity_type: str,
    operation: str,
    payload: dict,
    entity_uid: str | None = None,
    node_id: str | None = None,
) -> SyncOutboxEvent:
    event = SyncOutboxEvent(
        event_id=str(uuid.uuid4()),
        clinic_id=clinic_id,
        node_id=node_id or os.getenv("NODE_ID") or None,
        entity_type=entity_type,
        entity_uid=entity_uid,
        operation=operation,
        payload_json=json.dumps(payload, default=str),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_pending_outbox(db: Session, clinic_id: int, limit: int = 100) -> list[SyncOutboxEvent]:
    return (
        db.query(SyncOutboxEvent)
        .filter(SyncOutboxEvent.clinic_id == clinic_id, SyncOutboxEvent.acked_at.is_(None))
        .order_by(SyncOutboxEvent.id.asc())
        .limit(limit)
        .all()
    )


def ack_outbox_events(db: Session, event_ids: list[str]) -> int:
    rows = db.query(SyncOutboxEvent).filter(SyncOutboxEvent.event_id.in_(event_ids)).all()
    now = datetime.utcnow()
    for row in rows:
        row.acked_at = now
    db.commit()
    return len(rows)


def record_conflict(
    db: Session,
    *,
    clinic_id: int,
    entity_type: str,
    local_payload: dict,
    remote_payload: dict,
    entity_uid: str | None = None,
) -> SyncConflict:
    conflict = SyncConflict(
        clinic_id=clinic_id,
        entity_type=entity_type,
        entity_uid=entity_uid,
        local_json=json.dumps(local_payload, default=str),
        remote_json=json.dumps(remote_payload, default=str),
        status="open",
    )
    db.add(conflict)
    db.commit()
    db.refresh(conflict)
    return conflict


def ensure_local_license(db: Session, clinic_id: int, node_id: str | None = None) -> ClinicNodeLicense:
    existing = (
        db.query(ClinicNodeLicense)
        .filter(ClinicNodeLicense.clinic_id == clinic_id, ClinicNodeLicense.is_active.is_(True))
        .order_by(ClinicNodeLicense.id.desc())
        .first()
    )
    if existing:
        return existing

    issued = datetime.utcnow()
    valid_until = issued + timedelta(days=365)
    grace_until = valid_until + timedelta(days=180)
    token = {
        "clinic_id": clinic_id,
        "node_id": node_id or os.getenv("NODE_ID"),
        "plan": "offline-v1",
        "issued_at": issued.isoformat(),
        "valid_until": valid_until.isoformat(),
        "grace_until": grace_until.isoformat(),
    }
    license_row = ClinicNodeLicense(
        clinic_id=clinic_id,
        node_id=token["node_id"],
        plan="offline-v1",
        issued_at=issued,
        valid_until=valid_until,
        grace_until=grace_until,
        token_json=json.dumps(token),
        is_active=True,
    )
    db.add(license_row)
    db.commit()
    db.refresh(license_row)
    return license_row


def license_state(license_row: ClinicNodeLicense | None) -> str:
    if not license_row:
        return "missing"
    now = datetime.utcnow()
    if now <= license_row.valid_until:
        return "OK"
    if now <= license_row.grace_until:
        return "GRACE"
    return "EXPIRED"


def run_local_backup(backup_dir: str | Path | None = None) -> dict:
    """Create a local pg_dump backup into Clinic Node data/backups."""
    data_dir = Path(os.getenv("CLINIC_DATA_DIR") or "/clinic-data")
    if not data_dir.exists():
        # Host-side development fallback when not running in the appliance container.
        data_dir = Path("deploy/clinic-node/data")
    target = Path(backup_dir or (data_dir / "backups"))
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    outfile = target / f"clinic-node-{stamp}.sql.gz"

    database_url = os.getenv("DATABASE_URL") or ""
    min_valid_bytes = 200  # empty/header-only gzip is ~20 bytes

    def _finalize(path: Path, method: str) -> dict:
        size = path.stat().st_size if path.exists() else 0
        ok = size >= min_valid_bytes
        if not ok and path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        return {
            "ok": ok,
            "path": str(path if ok else ""),
            "bytes": size if ok else 0,
            "created_at": stamp,
            "method": method,
        }

    def _run_pipe(cmd: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-lc", f"set -euo pipefail; {cmd}"],
            check=True,
            capture_output=True,
            text=True,
        )

    # Prefer direct pg_dump against DATABASE_URL (works inside backend container).
    if database_url.startswith("postgresql"):
        try:
            _run_pipe(
                f"pg_dump --dbname={database_url!r} --no-owner --no-acl | gzip -c > {str(outfile)!r}"
            )
            result = _finalize(outfile, "pg_dump")
            if result["ok"]:
                return result
            logger.error("pg_dump produced undersized backup")
        except Exception as exc:
            logger.error("pg_dump via DATABASE_URL failed: %s", exc)

        # Explicit host/user/password form (avoids some URL parsing edge cases).
        try:
            user = os.getenv("POSTGRES_USER") or "sante"
            password = os.getenv("POSTGRES_PASSWORD") or ""
            dbname = os.getenv("POSTGRES_DB") or "sante"
            host = "127.0.0.1"
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = password
            subprocess.run(
                [
                    "bash",
                    "-lc",
                    "set -euo pipefail; "
                    f"pg_dump -h {host!r} -U {user!r} -d {dbname!r} --no-owner --no-acl "
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

        # Fallback: docker exec when API runs on host with compose db container.
        try:
            _run_pipe(
                "sudo docker exec clinic-node-db-1 pg_dump -U sante --no-owner --no-acl sante "
                f"| gzip -c > {str(outfile)!r}"
            )
            result = _finalize(outfile, "pg_dump_docker")
            if result["ok"]:
                return result
            logger.error("docker pg_dump produced undersized backup")
        except Exception as exc:
            logger.error("pg_dump docker backup failed: %s", exc)

    marker = target / f"clinic-node-{stamp}.marker"
    marker.write_text(f"backup-marker {stamp}\n", encoding="utf-8")
    return {
        "ok": False,
        "path": str(marker),
        "bytes": marker.stat().st_size,
        "created_at": stamp,
        "method": "marker",
        "error": "pg_dump unavailable; marker written only",
    }


def build_ops_heartbeat(db: Session, clinic_id: int) -> dict:
    node_id = os.getenv("NODE_ID") or "unknown-node"
    license_row = ensure_local_license(db, clinic_id, node_id=node_id)
    outbox_depth = (
        db.query(SyncOutboxEvent)
        .filter(SyncOutboxEvent.clinic_id == clinic_id, SyncOutboxEvent.acked_at.is_(None))
        .count()
    )
    data_dir = Path(os.getenv("CLINIC_DATA_DIR") or "/clinic-data")
    if not data_dir.exists():
        data_dir = Path("deploy/clinic-node/data")
    usage = shutil.disk_usage(str(data_dir if data_dir.exists() else "."))
    backups = sorted((data_dir / "backups").glob("*")) if (data_dir / "backups").exists() else []
    last_backup = None
    last_backup_dt = None
    if backups:
        last_backup_dt = datetime.utcfromtimestamp(backups[-1].stat().st_mtime)
        last_backup = last_backup_dt.isoformat() + "Z"

    payload = {
        "clinic_id": clinic_id,
        "node_id": node_id,
        "software_version": SOFTWARE_VERSION,
        "schema_version": "head",
        "node_status": "ONLINE",
        "disk_free_bytes": int(usage.free),
        "disk_total_bytes": int(usage.total),
        "outbox_depth": outbox_depth,
        "last_backup_local_at": last_backup,
        "last_sync_success_at": None,
        "license_state": license_state(license_row),
        "phi": False,
    }
    row = ClinicNodeHeartbeat(
        clinic_id=clinic_id,
        node_id=node_id,
        software_version=SOFTWARE_VERSION,
        schema_version="head",
        disk_free_bytes=int(usage.free),
        disk_total_bytes=int(usage.total),
        outbox_depth=outbox_depth,
        last_backup_local_at=last_backup_dt,
        license_state=payload["license_state"],
        payload_json=json.dumps(payload),
    )
    db.add(row)
    db.commit()
    return payload
