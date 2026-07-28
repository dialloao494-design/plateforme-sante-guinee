"""Clinic Node sync outbox / license / heartbeat models (Phase 3–4)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint

from database import Base


class SyncOutboxEvent(Base):
    __tablename__ = "sync_outbox_events"
    __table_args__ = (UniqueConstraint("event_id", name="uq_sync_outbox_event_id"),)

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), nullable=False, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    node_id = Column(String(64), nullable=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_uid = Column(String(64), nullable=True, index=True)
    operation = Column(String(32), nullable=False)  # create|update|delete|movement
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    acked_at = Column(DateTime, nullable=True)
    ack_error = Column(Text, nullable=True)


class SyncConflict(Base):
    __tablename__ = "sync_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_uid = Column(String(64), nullable=True)
    local_json = Column(Text, nullable=False)
    remote_json = Column(Text, nullable=False)
    status = Column(String(32), default="open", nullable=False)  # open|resolved
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)


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
    is_active = Column(Boolean, default=True, nullable=False)
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
