"""Clinic Node conflict engine — versioning, merge policies, manual resolve, audit."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.clinic_node_ops import SyncAuditLog, SyncConflict

logger = logging.getLogger(__name__)

ResolutionPolicy = Literal["local_wins", "remote_wins", "merge", "manual"]


def record_conflict(
    db: Session,
    *,
    clinic_id: int,
    entity_type: str,
    local_payload: dict,
    remote_payload: dict,
    entity_uid: str | None = None,
    local_version: int | None = None,
    remote_version: int | None = None,
) -> SyncConflict:
    conflict = SyncConflict(
        clinic_id=clinic_id,
        entity_type=entity_type,
        entity_uid=entity_uid,
        local_version=local_version,
        remote_version=remote_version,
        local_json=json.dumps(local_payload, default=str),
        remote_json=json.dumps(remote_payload, default=str),
        status="open",
    )
    db.add(conflict)
    db.add(
        SyncAuditLog(
            clinic_id=clinic_id,
            action="conflict_recorded",
            entity_type=entity_type,
            entity_uid=entity_uid,
            detail_json=json.dumps(
                {"local_version": local_version, "remote_version": remote_version}, default=str
            ),
        )
    )
    db.commit()
    db.refresh(conflict)
    return conflict


def _deep_merge(local: dict, remote: dict) -> dict:
    """Field-level merge: remote fills missing keys; conflicting scalars prefer remote with local kept under _local_*."""
    out = dict(remote)
    for key, lval in local.items():
        if key not in remote:
            out[key] = lval
        elif isinstance(lval, dict) and isinstance(remote.get(key), dict):
            out[key] = _deep_merge(lval, remote[key])
        elif lval != remote.get(key):
            out[key] = remote[key]
            out[f"_local_{key}"] = lval
    return out


def resolve_conflict(
    db: Session,
    *,
    conflict_id: int,
    clinic_id: int,
    policy: ResolutionPolicy,
    resolved_by_user_id: int | None = None,
    manual_payload: dict[str, Any] | None = None,
    note: str | None = None,
) -> SyncConflict:
    conflict = (
        db.query(SyncConflict)
        .filter(SyncConflict.id == conflict_id, SyncConflict.clinic_id == clinic_id)
        .first()
    )
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    if conflict.status == "resolved":
        return conflict

    local = json.loads(conflict.local_json)
    remote = json.loads(conflict.remote_json)

    if policy == "local_wins":
        merged = local
    elif policy == "remote_wins":
        merged = remote
    elif policy == "merge":
        if not isinstance(local, dict) or not isinstance(remote, dict):
            raise HTTPException(status_code=400, detail="merge policy requires object payloads")
        merged = _deep_merge(local, remote)
    elif policy == "manual":
        if manual_payload is None:
            raise HTTPException(status_code=400, detail="manual_payload required for manual policy")
        merged = manual_payload
    else:
        raise HTTPException(status_code=400, detail=f"Unknown policy: {policy}")

    conflict.merged_json = json.dumps(merged, default=str)
    conflict.resolution_policy = policy
    conflict.status = "resolved"
    conflict.resolved_at = datetime.utcnow()
    conflict.resolved_by_user_id = resolved_by_user_id
    conflict.resolution_note = note
    db.add(
        SyncAuditLog(
            clinic_id=clinic_id,
            action="conflict_resolved",
            entity_type=conflict.entity_type,
            entity_uid=conflict.entity_uid,
            detail_json=json.dumps(
                {
                    "conflict_id": conflict.id,
                    "policy": policy,
                    "resolved_by_user_id": resolved_by_user_id,
                    "note": note,
                },
                default=str,
            ),
        )
    )
    db.commit()
    db.refresh(conflict)
    return conflict


def list_open_conflicts(db: Session, clinic_id: int, limit: int = 100) -> list[SyncConflict]:
    return (
        db.query(SyncConflict)
        .filter(SyncConflict.clinic_id == clinic_id, SyncConflict.status == "open")
        .order_by(SyncConflict.id.desc())
        .limit(limit)
        .all()
    )
