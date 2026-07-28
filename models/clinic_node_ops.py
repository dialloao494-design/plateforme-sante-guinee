"""Clinic Node production ops models — license, sync, conflicts, audit, backups."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from database import Base


class SyncOutboxEvent(Base):
    __tablename__ = "sync_outbox_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_sync_outbox_event_id"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), nullable=False, index=True)
    client_request_id = Column(String(64), nullable=True, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    node_id = Column(String(64), nullable=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_uid = Column(String(64), nullable=True, index=True)
    operation = Column(String(32), nullable=False)
    payload_json = Column(Text, nullable=False)
    record_version = Column(Integer, nullable=False, default=1)
    attempt_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    # pending | in_flight | acked | dead
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    acked_at = Column(DateTime, nullable=True)
    ack_error = Column(Text, nullable=True)


class SyncInboxEvent(Base):
    """Idempotent ingest log for cloud→node or node↔mirror sync."""

    __tablename__ = "sync_inbox_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_sync_inbox_event_id"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), nullable=False, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_uid = Column(String(64), nullable=True)
    operation = Column(String(32), nullable=False)
    payload_json = Column(Text, nullable=False)
    record_version = Column(Integer, nullable=False, default=1)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    applied = Column(Boolean, default=True, nullable=False)


class SyncConflict(Base):
    __tablename__ = "sync_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_uid = Column(String(64), nullable=True)
    local_version = Column(Integer, nullable=True)
    remote_version = Column(Integer, nullable=True)
    local_json = Column(Text, nullable=False)
    remote_json = Column(Text, nullable=False)
    merged_json = Column(Text, nullable=True)
    status = Column(String(32), default="open", nullable=False)  # open|resolved
    resolution_policy = Column(String(32), nullable=True)  # local_wins|remote_wins|merge|manual
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_user_id = Column(Integer, nullable=True)
    resolution_note = Column(Text, nullable=True)


class SyncAuditLog(Base):
    __tablename__ = "sync_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=True)
    entity_uid = Column(String(64), nullable=True)
    event_id = Column(String(64), nullable=True, index=True)
    detail_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClinicNodeLicense(Base):
    __tablename__ = "clinic_node_licenses"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    node_id = Column(String(64), nullable=True)
    plan = Column(String(64), default="offline-v1", nullable=False)
    issued_at = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    grace_until = Column(DateTime, nullable=False)
    token_json = Column(Text, nullable=False)
    signature = Column(String(128), nullable=False, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    last_validated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClinicNodeHeartbeat(Base):
    __tablename__ = "clinic_node_heartbeats"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    node_id = Column(String(64), nullable=False, index=True)
    software_version = Column(String(64), nullable=True)
    schema_version = Column(String(64), nullable=True)
    disk_free_bytes = Column(BigInteger, nullable=True)
    disk_total_bytes = Column(BigInteger, nullable=True)
    outbox_depth = Column(Integer, nullable=True)
    last_backup_local_at = Column(DateTime, nullable=True)
    last_sync_success_at = Column(DateTime, nullable=True)
    license_state = Column(String(32), nullable=True)
    payload_json = Column(Text, nullable=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ClinicNodeBackupRecord(Base):
    __tablename__ = "clinic_node_backup_records"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, nullable=True, index=True)
    path = Column(String(512), nullable=False)
    sha256 = Column(String(64), nullable=False)
    bytes = Column(BigInteger, nullable=False, default=0)
    verified = Column(Boolean, default=False, nullable=False)
    method = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    restored_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
