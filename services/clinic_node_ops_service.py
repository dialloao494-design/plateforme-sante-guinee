"""Clinic Node ops facade — heartbeat + re-exports for routers/tests."""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from models.clinic_node_ops import ClinicNodeHeartbeat, SyncOutboxEvent
from services.clinic_node_backup_service import run_local_backup as _run_backup
from services.clinic_node_license_service import (
    activate_or_renew_license,
    get_active_license,
    license_state_from_row,
)
from services.clinic_node_sync_service import last_sync_success_at

logger = logging.getLogger(__name__)
SOFTWARE_VERSION = os.getenv("CLINIC_NODE_SOFTWARE_VERSION", "offline-v1.0.0")


def ensure_local_license(db: Session, clinic_id: int, node_id: str | None = None):
    """Backward-compatible: activate signed license if missing."""
    return activate_or_renew_license(db, clinic_id=clinic_id, node_id=node_id, renew=False)


def license_state(license_row) -> str:
    return license_state_from_row(license_row)


def run_local_backup(backup_dir=None, db: Session | None = None, clinic_id: int | None = None) -> dict:
    # backup_dir retained for API compat; service uses CLINIC_DATA_DIR.
    return _run_backup(db=db, clinic_id=clinic_id)


def build_ops_heartbeat(db: Session, clinic_id: int) -> dict:
    node_id = os.getenv("NODE_ID") or "unknown-node"
    license_row = get_active_license(db, clinic_id)
    if not license_row:
        license_row = activate_or_renew_license(db, clinic_id=clinic_id, node_id=node_id)
    outbox_depth = (
        db.query(SyncOutboxEvent)
        .filter(
            SyncOutboxEvent.clinic_id == clinic_id,
            SyncOutboxEvent.status.in_(("pending", "in_flight")),
        )
        .count()
    )
    data_dir = Path(os.getenv("CLINIC_DATA_DIR") or "/clinic-data")
    if not data_dir.exists():
        data_dir = Path("deploy/clinic-node/data")
    usage = shutil.disk_usage(str(data_dir if data_dir.exists() else "."))
    backups = sorted((data_dir / "backups").glob("clinic-node-*.sql.gz")) if (data_dir / "backups").exists() else []
    last_backup = None
    last_backup_dt = None
    if backups:
        last_backup_dt = datetime.utcfromtimestamp(backups[-1].stat().st_mtime)
        last_backup = last_backup_dt.isoformat() + "Z"
    sync_at = last_sync_success_at(db, clinic_id)

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
        "last_sync_success_at": sync_at.isoformat() + "Z" if sync_at else None,
        "license_state": license_state_from_row(license_row, node_id=node_id),
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
        last_sync_success_at=sync_at,
        license_state=payload["license_state"],
        payload_json=json.dumps(payload),
    )
    db.add(row)
    db.commit()
    return payload


# Re-exports used by older imports
from services.clinic_node_sync_service import (  # noqa: E402
    ack_outbox_events,
    enqueue_outbox_event,
    list_pending_outbox,
)
from services.clinic_node_conflict_service import record_conflict  # noqa: E402
