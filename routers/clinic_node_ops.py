"""Clinic Node ops API — sync outbox, license, backup, heartbeat, owner view (no PHI)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.clinic_node_ops import SyncConflict, SyncOutboxEvent
from models.user import User
from core.clinical_access import assert_role
from security import get_current_user
from services.clinic_node_ops_service import (
    ack_outbox_events,
    build_ops_heartbeat,
    enqueue_outbox_event,
    ensure_local_license,
    license_state,
    list_pending_outbox,
    record_conflict,
    run_local_backup,
)

router = APIRouter(prefix="/clinic-node", tags=["Clinic Node Ops"])


class OutboxEnqueueRequest(BaseModel):
    entity_type: str
    operation: str
    payload: dict[str, Any] = Field(default_factory=dict)
    entity_uid: str | None = None


class OutboxAckRequest(BaseModel):
    event_ids: list[str]


class ConflictRequest(BaseModel):
    entity_type: str
    entity_uid: str | None = None
    local_payload: dict[str, Any]
    remote_payload: dict[str, Any]


def _clinic_id(user: User) -> int:
    if not user.clinic_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a clinic")
    return int(user.clinic_id)


@router.get("/health-ops")
def clinic_node_health_ops(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Ops health for the local node — no patient fields."""
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    clinic_id = _clinic_id(current_user)
    return build_ops_heartbeat(db, clinic_id)


@router.post("/backup/run")
def clinic_node_backup_run(current_user: User = Depends(get_current_user)):
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    result = run_local_backup()
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail="Backup failed")
    return result


@router.get("/license")
def clinic_node_license(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    clinic_id = _clinic_id(current_user)
    row = ensure_local_license(db, clinic_id, node_id=os.getenv("NODE_ID"))
    return {
        "clinic_id": row.clinic_id,
        "plan": row.plan,
        "valid_until": row.valid_until.isoformat() + "Z",
        "grace_until": row.grace_until.isoformat() + "Z",
        "state": license_state(row),
    }


@router.get("/sync/outbox")
def clinic_node_outbox(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    clinic_id = _clinic_id(current_user)
    rows = list_pending_outbox(db, clinic_id)
    return [
        {
            "event_id": r.event_id,
            "entity_type": r.entity_type,
            "operation": r.operation,
            "entity_uid": r.entity_uid,
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]


@router.post("/sync/outbox")
def clinic_node_outbox_enqueue(
    body: OutboxEnqueueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    clinic_id = _clinic_id(current_user)
    event = enqueue_outbox_event(
        db,
        clinic_id=clinic_id,
        entity_type=body.entity_type,
        operation=body.operation,
        payload=body.payload,
        entity_uid=body.entity_uid,
    )
    return {"event_id": event.event_id, "queued": True}


@router.post("/sync/outbox/ack")
def clinic_node_outbox_ack(
    body: OutboxAckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    return {"acked": ack_outbox_events(db, body.event_ids)}


@router.post("/sync/conflicts")
def clinic_node_conflict(
    body: ConflictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    conflict = record_conflict(
        db,
        clinic_id=_clinic_id(current_user),
        entity_type=body.entity_type,
        entity_uid=body.entity_uid,
        local_payload=body.local_payload,
        remote_payload=body.remote_payload,
    )
    return {"id": conflict.id, "status": conflict.status}


@router.get("/sync/conflicts")
def clinic_node_conflicts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    rows = (
        db.query(SyncConflict)
        .filter(SyncConflict.clinic_id == _clinic_id(current_user), SyncConflict.status == "open")
        .order_by(SyncConflict.id.desc())
        .limit(100)
        .all()
    )
    return [{"id": r.id, "entity_type": r.entity_type, "entity_uid": r.entity_uid, "status": r.status} for r in rows]


@router.get("/owner/dashboard")
def owner_dashboard_local(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Owner-style supervision for this node (ops fields only, no PHI).
    On multi-clinic cloud this will later aggregate heartbeats; locally it reports this node.
    """
    assert_role(current_user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))
    heartbeat = build_ops_heartbeat(db, _clinic_id(current_user))
    return {
        "clinics": [
            {
                "clinic_id": heartbeat["clinic_id"],
                "node_id": heartbeat["node_id"],
                "status": heartbeat["node_status"],
                "software_version": heartbeat["software_version"],
                "outbox_depth": heartbeat["outbox_depth"],
                "disk_free_bytes": heartbeat["disk_free_bytes"],
                "last_backup_local_at": heartbeat["last_backup_local_at"],
                "license_state": heartbeat["license_state"],
            }
        ]
    }
