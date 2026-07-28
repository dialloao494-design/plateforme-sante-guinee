"""Clinic Node ops API — license, sync, conflicts, backup/restore, owner view."""

from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.clinic_node_ops import SyncAuditLog, SyncConflict, SyncOutboxEvent
from models.user import User
from core.clinical_access import assert_role
from security import get_current_user
from services.clinic_node_backup_service import restore_backup, run_local_backup, verify_backup_file
from services.clinic_node_conflict_service import list_open_conflicts, record_conflict, resolve_conflict
from services.clinic_node_license_service import (
    activate_or_renew_license,
    get_active_license,
    import_signed_license_token,
    license_state_from_row,
)
from services.clinic_node_ops_service import build_ops_heartbeat
from services.clinic_node_sync_service import (
    ack_outbox_events,
    enqueue_outbox_event,
    ingest_sync_event,
    list_pending_outbox,
    push_pending_to_cloud,
)

router = APIRouter(prefix="/clinic-node", tags=["Clinic Node Ops"])


class OutboxEnqueueRequest(BaseModel):
    entity_type: str
    operation: str
    payload: dict[str, Any] = Field(default_factory=dict)
    entity_uid: str | None = None
    client_request_id: str | None = None
    record_version: int = 1


class OutboxAckRequest(BaseModel):
    event_ids: list[str]


class ConflictRequest(BaseModel):
    entity_type: str
    entity_uid: str | None = None
    local_payload: dict[str, Any]
    remote_payload: dict[str, Any]
    local_version: int | None = None
    remote_version: int | None = None


class ConflictResolveRequest(BaseModel):
    policy: Literal["local_wins", "remote_wins", "merge", "manual"]
    manual_payload: dict[str, Any] | None = None
    note: str | None = None


class LicenseImportRequest(BaseModel):
    token_json: str
    signature: str


class LicenseRenewRequest(BaseModel):
    valid_days: int | None = None
    grace_days: int | None = None


class RestoreRequest(BaseModel):
    path: str
    confirm: bool = False
    dry_run: bool = False


class SyncIngestEnvelope(BaseModel):
    event_id: str
    client_request_id: str | None = None
    clinic_id: int
    node_id: str | None = None
    entity_type: str
    entity_uid: str | None = None
    operation: str
    record_version: int = 1
    payload: dict[str, Any] = Field(default_factory=dict)


def _clinic_id(user: User) -> int:
    if not user.clinic_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a clinic")
    return int(user.clinic_id)


def _admin(user: User) -> None:
    assert_role(user, ("clinic_admin", "admin", "platform_owner", "platform_admin"))


@router.get("/health-ops")
def clinic_node_health_ops(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    return build_ops_heartbeat(db, _clinic_id(current_user))


@router.post("/backup/run")
def clinic_node_backup_run(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    result = run_local_backup(db=db, clinic_id=_clinic_id(current_user))
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error") or "Backup failed")
    return result


@router.post("/backup/verify")
def clinic_node_backup_verify(body: RestoreRequest, current_user: User = Depends(get_current_user)):
    _admin(current_user)
    return verify_backup_file(__import__("pathlib").Path(body.path))


@router.post("/backup/restore")
def clinic_node_backup_restore(body: RestoreRequest, current_user: User = Depends(get_current_user)):
    _admin(current_user)
    if body.dry_run:
        return restore_backup(body.path, dry_run=True)
    if not body.confirm:
        raise HTTPException(status_code=400, detail="confirm=true required for destructive restore")
    if os.getenv("CLINIC_NODE_ALLOW_RESTORE", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(
            status_code=403,
            detail="Set CLINIC_NODE_ALLOW_RESTORE=true to enable restore API",
        )
    result = restore_backup(body.path, dry_run=False)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result)
    return result


@router.get("/license")
def clinic_node_license(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    clinic_id = _clinic_id(current_user)
    row = get_active_license(db, clinic_id)
    if not row:
        row = activate_or_renew_license(db, clinic_id=clinic_id, node_id=os.getenv("NODE_ID"))
    state = license_state_from_row(row, node_id=os.getenv("NODE_ID"))
    return {
        "clinic_id": row.clinic_id,
        "node_id": row.node_id,
        "plan": row.plan,
        "valid_until": row.valid_until.isoformat() + "Z",
        "grace_until": row.grace_until.isoformat() + "Z",
        "state": state,
        "signature_present": bool(row.signature),
        "activated_at": row.activated_at.isoformat() + "Z" if row.activated_at else None,
    }


@router.post("/license/activate")
def clinic_node_license_activate(
    body: LicenseRenewRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _admin(current_user)
    body = body or LicenseRenewRequest()
    row = activate_or_renew_license(
        db,
        clinic_id=_clinic_id(current_user),
        node_id=os.getenv("NODE_ID"),
        valid_days=body.valid_days,
        grace_days=body.grace_days,
        renew=False,
    )
    return {"state": license_state_from_row(row), "clinic_id": row.clinic_id, "signature": row.signature[:16] + "…"}


@router.post("/license/renew")
def clinic_node_license_renew(
    body: LicenseRenewRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _admin(current_user)
    body = body or LicenseRenewRequest()
    row = activate_or_renew_license(
        db,
        clinic_id=_clinic_id(current_user),
        node_id=os.getenv("NODE_ID"),
        valid_days=body.valid_days,
        grace_days=body.grace_days,
        renew=True,
    )
    return {
        "state": license_state_from_row(row),
        "valid_until": row.valid_until.isoformat() + "Z",
        "grace_until": row.grace_until.isoformat() + "Z",
    }


@router.post("/license/import")
def clinic_node_license_import(
    body: LicenseImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _admin(current_user)
    row = import_signed_license_token(
        db,
        clinic_id=_clinic_id(current_user),
        token_json=body.token_json,
        signature=body.signature,
        node_id=os.getenv("NODE_ID"),
    )
    return {"state": license_state_from_row(row), "clinic_id": row.clinic_id}


@router.get("/sync/outbox")
def clinic_node_outbox(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    rows = list_pending_outbox(db, _clinic_id(current_user))
    return [
        {
            "event_id": r.event_id,
            "client_request_id": r.client_request_id,
            "entity_type": r.entity_type,
            "operation": r.operation,
            "entity_uid": r.entity_uid,
            "record_version": r.record_version,
            "attempt_count": r.attempt_count,
            "status": r.status,
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
    _admin(current_user)
    event = enqueue_outbox_event(
        db,
        clinic_id=_clinic_id(current_user),
        entity_type=body.entity_type,
        operation=body.operation,
        payload=body.payload,
        entity_uid=body.entity_uid,
        client_request_id=body.client_request_id,
        record_version=body.record_version,
    )
    return {"event_id": event.event_id, "queued": True, "duplicate": False}


@router.post("/sync/outbox/ack")
def clinic_node_outbox_ack(
    body: OutboxAckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _admin(current_user)
    return {"acked": ack_outbox_events(db, body.event_ids)}


@router.post("/sync/push")
def clinic_node_sync_push(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    return push_pending_to_cloud(db, _clinic_id(current_user))


@router.post("/sync/ingest")
def clinic_node_sync_ingest(
    body: SyncIngestEnvelope,
    db: Session = Depends(get_db),
    x_sync_token: str | None = Header(default=None, alias="X-Sync-Token"),
):
    """Cloud or peer ingest — authenticated via shared sync token when configured."""
    expected = os.getenv("CLINIC_NODE_SYNC_TOKEN") or ""
    if expected and x_sync_token != expected:
        raise HTTPException(status_code=401, detail="Invalid sync token")
    return ingest_sync_event(db, body.model_dump(), source="ingest_api")


@router.post("/sync/conflicts")
def clinic_node_conflict(
    body: ConflictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _admin(current_user)
    conflict = record_conflict(
        db,
        clinic_id=_clinic_id(current_user),
        entity_type=body.entity_type,
        entity_uid=body.entity_uid,
        local_payload=body.local_payload,
        remote_payload=body.remote_payload,
        local_version=body.local_version,
        remote_version=body.remote_version,
    )
    return {"id": conflict.id, "status": conflict.status}


@router.get("/sync/conflicts")
def clinic_node_conflicts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
    rows = list_open_conflicts(db, _clinic_id(current_user))
    return [
        {
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_uid": r.entity_uid,
            "status": r.status,
            "local_version": r.local_version,
            "remote_version": r.remote_version,
        }
        for r in rows
    ]


@router.post("/sync/conflicts/{conflict_id}/resolve")
def clinic_node_conflict_resolve(
    conflict_id: int,
    body: ConflictResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _admin(current_user)
    conflict = resolve_conflict(
        db,
        conflict_id=conflict_id,
        clinic_id=_clinic_id(current_user),
        policy=body.policy,
        resolved_by_user_id=current_user.id,
        manual_payload=body.manual_payload,
        note=body.note,
    )
    return {
        "id": conflict.id,
        "status": conflict.status,
        "resolution_policy": conflict.resolution_policy,
        "merged_json": conflict.merged_json,
    }


@router.get("/sync/audit")
def clinic_node_sync_audit(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _admin(current_user)
    rows = (
        db.query(SyncAuditLog)
        .filter(SyncAuditLog.clinic_id == _clinic_id(current_user))
        .order_by(SyncAuditLog.id.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": r.id,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_uid": r.entity_uid,
            "event_id": r.event_id,
            "created_at": r.created_at.isoformat() + "Z",
        }
        for r in rows
    ]


@router.get("/owner/dashboard")
def owner_dashboard_local(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _admin(current_user)
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
                "last_sync_success_at": heartbeat["last_sync_success_at"],
                "license_state": heartbeat["license_state"],
            }
        ]
    }
