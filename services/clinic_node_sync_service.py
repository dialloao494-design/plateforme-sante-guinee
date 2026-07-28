"""Clinic Node delta sync — outbox queue, retry, resume, dedupe, ingest, audit."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from models.clinic_node_ops import (
    SyncAuditLog,
    SyncConflict,
    SyncInboxEvent,
    SyncOutboxEvent,
)

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = int(os.getenv("CLINIC_NODE_SYNC_MAX_ATTEMPTS", "12"))
BASE_BACKOFF_SECONDS = int(os.getenv("CLINIC_NODE_SYNC_BACKOFF_SECONDS", "30"))


def _audit(
    db: Session,
    *,
    clinic_id: int,
    action: str,
    entity_type: str | None = None,
    entity_uid: str | None = None,
    event_id: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        SyncAuditLog(
            clinic_id=clinic_id,
            action=action,
            entity_type=entity_type,
            entity_uid=entity_uid,
            event_id=event_id,
            detail_json=json.dumps(detail or {}, default=str),
        )
    )


def enqueue_outbox_event(
    db: Session,
    *,
    clinic_id: int,
    entity_type: str,
    operation: str,
    payload: dict,
    entity_uid: str | None = None,
    node_id: str | None = None,
    client_request_id: str | None = None,
    record_version: int = 1,
    commit: bool = True,
) -> SyncOutboxEvent:
    """Enqueue with duplicate prevention via client_request_id."""
    req_id = client_request_id or str(uuid.uuid4())
    existing = (
        db.query(SyncOutboxEvent)
        .filter(SyncOutboxEvent.client_request_id == req_id)
        .first()
    )
    if existing:
        return existing

    event = SyncOutboxEvent(
        event_id=str(uuid.uuid4()),
        client_request_id=req_id,
        clinic_id=clinic_id,
        node_id=node_id or os.getenv("NODE_ID") or None,
        entity_type=entity_type,
        entity_uid=entity_uid,
        operation=operation,
        payload_json=json.dumps(payload, default=str),
        record_version=record_version,
        attempt_count=0,
        status="pending",
    )
    db.add(event)
    _audit(
        db,
        clinic_id=clinic_id,
        action="outbox_enqueue",
        entity_type=entity_type,
        entity_uid=entity_uid,
        event_id=event.event_id,
        detail={"operation": operation, "client_request_id": req_id},
    )
    if commit:
        db.commit()
        db.refresh(event)
    return event


def list_pending_outbox(db: Session, clinic_id: int, limit: int = 100) -> list[SyncOutboxEvent]:
    now = datetime.utcnow()
    return (
        db.query(SyncOutboxEvent)
        .filter(
            SyncOutboxEvent.clinic_id == clinic_id,
            SyncOutboxEvent.status.in_(("pending", "in_flight")),
            SyncOutboxEvent.acked_at.is_(None),
            (SyncOutboxEvent.next_retry_at.is_(None) | (SyncOutboxEvent.next_retry_at <= now)),
        )
        .order_by(SyncOutboxEvent.id.asc())
        .limit(limit)
        .all()
    )


def ack_outbox_events(db: Session, event_ids: list[str], error: str | None = None) -> int:
    rows = db.query(SyncOutboxEvent).filter(SyncOutboxEvent.event_id.in_(event_ids)).all()
    now = datetime.utcnow()
    for row in rows:
        if error:
            row.ack_error = error
            row.status = "dead"
            row.last_error = error
        else:
            row.acked_at = now
            row.status = "acked"
            row.ack_error = None
        _audit(
            db,
            clinic_id=row.clinic_id,
            action="outbox_ack" if not error else "outbox_dead",
            entity_type=row.entity_type,
            entity_uid=row.entity_uid,
            event_id=row.event_id,
        )
    db.commit()
    return len(rows)


def _backoff(attempt: int) -> datetime:
    seconds = min(3600, BASE_BACKOFF_SECONDS * (2 ** max(0, attempt - 1)))
    return datetime.utcnow() + timedelta(seconds=seconds)


def push_pending_to_cloud(db: Session, clinic_id: int, limit: int = 50) -> dict[str, Any]:
    """
    Push pending outbox events to CLOUD_SYNC_URL (or local mirror ingest).
    Resumes after outages via next_retry_at + attempt_count.
    """
    cloud_url = (os.getenv("CLOUD_SYNC_URL") or "").rstrip("/")
    local_ingest = os.getenv("CLINIC_NODE_SYNC_LOCAL_MIRROR", "true").lower() in ("1", "true", "yes")
    pending = list_pending_outbox(db, clinic_id, limit=limit)
    pushed = 0
    failed = 0
    conflicts = 0

    for row in pending:
        row.status = "in_flight"
        row.attempt_count = int(row.attempt_count or 0) + 1
        db.commit()

        envelope = {
            "event_id": row.event_id,
            "client_request_id": row.client_request_id,
            "clinic_id": row.clinic_id,
            "node_id": row.node_id,
            "entity_type": row.entity_type,
            "entity_uid": row.entity_uid,
            "operation": row.operation,
            "record_version": row.record_version,
            "payload": json.loads(row.payload_json),
        }

        try:
            if cloud_url:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(f"{cloud_url}/api/clinic-node/sync/ingest", json=envelope)
                    if resp.status_code >= 400:
                        raise RuntimeError(f"cloud HTTP {resp.status_code}: {resp.text[:200]}")
                    body = resp.json() if resp.content else {}
            elif local_ingest:
                body = ingest_sync_event(db, envelope, source="local_mirror")
            else:
                raise RuntimeError("CLOUD_SYNC_URL not configured")

            if body.get("conflict"):
                conflicts += 1
                row.status = "acked"
                row.acked_at = datetime.utcnow()
                row.ack_error = "conflict_recorded"
            else:
                row.status = "acked"
                row.acked_at = datetime.utcnow()
                row.last_error = None
            pushed += 1
            _audit(
                db,
                clinic_id=clinic_id,
                action="outbox_push_ok",
                entity_type=row.entity_type,
                entity_uid=row.entity_uid,
                event_id=row.event_id,
                detail={"mirror": bool(local_ingest and not cloud_url)},
            )
            db.commit()
        except Exception as exc:
            failed += 1
            row.last_error = str(exc)[:500]
            row.status = "pending"
            if row.attempt_count >= MAX_ATTEMPTS:
                row.status = "dead"
                _audit(
                    db,
                    clinic_id=clinic_id,
                    action="outbox_push_dead",
                    event_id=row.event_id,
                    detail={"error": str(exc)[:300]},
                )
            else:
                row.next_retry_at = _backoff(row.attempt_count)
                _audit(
                    db,
                    clinic_id=clinic_id,
                    action="outbox_push_retry",
                    event_id=row.event_id,
                    detail={"attempt": row.attempt_count, "error": str(exc)[:300]},
                )
            db.commit()
            logger.warning("sync push failed event=%s: %s", row.event_id, exc)

    return {
        "pending_seen": len(pending),
        "pushed": pushed,
        "failed": failed,
        "conflicts": conflicts,
        "cloud_url_configured": bool(cloud_url),
        "local_mirror": local_ingest and not cloud_url,
    }


def ingest_sync_event(db: Session, envelope: dict[str, Any], source: str = "cloud") -> dict[str, Any]:
    """
    Idempotent ingest. Detects version conflicts and records SyncConflict.
    """
    event_id = str(envelope.get("event_id") or "")
    if not event_id:
        raise ValueError("event_id required")

    existing = db.query(SyncInboxEvent).filter(SyncInboxEvent.event_id == event_id).first()
    if existing:
        _audit(db, clinic_id=existing.clinic_id, action="inbox_duplicate", event_id=event_id)
        db.commit()
        return {"ok": True, "duplicate": True, "conflict": False}

    clinic_id = int(envelope["clinic_id"])
    entity_type = str(envelope.get("entity_type") or "")
    entity_uid = envelope.get("entity_uid")
    remote_version = int(envelope.get("record_version") or 1)
    payload = envelope.get("payload") or {}

    # Conflict detection: if we have a newer/local pending outbox for same entity with different version.
    local = (
        db.query(SyncOutboxEvent)
        .filter(
            SyncOutboxEvent.clinic_id == clinic_id,
            SyncOutboxEvent.entity_type == entity_type,
            SyncOutboxEvent.entity_uid == str(entity_uid) if entity_uid is not None else None,
            SyncOutboxEvent.status.in_(("pending", "in_flight", "acked")),
        )
        .order_by(SyncOutboxEvent.id.desc())
        .first()
    )
    conflict = False
    if local and int(local.record_version or 1) != remote_version and local.event_id != event_id:
        try:
            local_payload = json.loads(local.payload_json)
        except Exception:
            local_payload = {}
        conflict_row = SyncConflict(
            clinic_id=clinic_id,
            entity_type=entity_type,
            entity_uid=str(entity_uid) if entity_uid is not None else None,
            local_version=int(local.record_version or 1),
            remote_version=remote_version,
            local_json=json.dumps(local_payload, default=str),
            remote_json=json.dumps(payload, default=str),
            status="open",
        )
        db.add(conflict_row)
        conflict = True
        _audit(
            db,
            clinic_id=clinic_id,
            action="conflict_detected",
            entity_type=entity_type,
            entity_uid=str(entity_uid) if entity_uid else None,
            event_id=event_id,
            detail={"local_version": local.record_version, "remote_version": remote_version},
        )

    inbox = SyncInboxEvent(
        event_id=event_id,
        clinic_id=clinic_id,
        entity_type=entity_type,
        entity_uid=str(entity_uid) if entity_uid is not None else None,
        operation=str(envelope.get("operation") or "upsert"),
        payload_json=json.dumps(payload, default=str),
        record_version=remote_version,
        applied=not conflict,
    )
    db.add(inbox)
    _audit(
        db,
        clinic_id=clinic_id,
        action="inbox_ingest",
        entity_type=entity_type,
        entity_uid=str(entity_uid) if entity_uid else None,
        event_id=event_id,
        detail={"source": source, "conflict": conflict},
    )
    db.commit()
    return {"ok": True, "duplicate": False, "conflict": conflict, "inbox_id": inbox.id}


def last_sync_success_at(db: Session, clinic_id: int) -> datetime | None:
    row = (
        db.query(SyncAuditLog)
        .filter(SyncAuditLog.clinic_id == clinic_id, SyncAuditLog.action == "outbox_push_ok")
        .order_by(SyncAuditLog.id.desc())
        .first()
    )
    return row.created_at if row else None
