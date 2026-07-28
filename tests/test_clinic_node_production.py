"""Unit tests for Clinic Node production offline capabilities."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from models.clinic_node_ops import ClinicNodeLicense, SyncConflict, SyncOutboxEvent
from services.clinic_node_conflict_service import record_conflict, resolve_conflict
from services.clinic_node_license_service import (
    activate_or_renew_license,
    build_signed_license,
    license_state_from_row,
    sign_license_claims,
    verify_license_signature,
)
from services.clinic_node_sync_service import enqueue_outbox_event, ingest_sync_event, push_pending_to_cloud


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestLicenseCrypto:
    def test_sign_and_verify(self, monkeypatch):
        monkeypatch.setenv("CLINIC_NODE_LICENSE_SECRET", "x" * 48)
        claims, sig, *_ = build_signed_license(clinic_id=7, node_id="node-a")
        assert verify_license_signature(claims, sig)
        assert not verify_license_signature(claims, "0" * 64)

    def test_activate_and_state_ok(self, db, monkeypatch):
        monkeypatch.setenv("CLINIC_NODE_LICENSE_SECRET", "y" * 48)
        monkeypatch.setenv("NODE_ID", "node-a")
        row = activate_or_renew_license(db, clinic_id=1, node_id="node-a")
        assert license_state_from_row(row, node_id="node-a") == "OK"
        assert row.signature

    def test_expired_state(self, db, monkeypatch):
        monkeypatch.setenv("CLINIC_NODE_LICENSE_SECRET", "z" * 48)
        monkeypatch.setenv("NODE_ID", "node-a")
        row = activate_or_renew_license(db, clinic_id=1, node_id="node-a", valid_days=0, grace_days=0)
        # Force past grace
        row.valid_until = datetime.utcnow() - timedelta(days=2)
        row.grace_until = datetime.utcnow() - timedelta(days=1)
        # Re-sign with matching claims
        claims = json.loads(row.token_json)
        claims["valid_until"] = row.valid_until.isoformat() + "Z"
        claims["grace_until"] = row.grace_until.isoformat() + "Z"
        row.token_json = json.dumps(claims, sort_keys=True, separators=(",", ":"))
        row.signature = sign_license_claims(claims)
        db.commit()
        assert license_state_from_row(row, node_id="node-a") == "EXPIRED"


class TestSyncQueue:
    def test_dedupe_client_request_id(self, db):
        a = enqueue_outbox_event(
            db,
            clinic_id=1,
            entity_type="patient",
            operation="create",
            payload={"id": 1},
            entity_uid="1",
            client_request_id="req-1",
        )
        b = enqueue_outbox_event(
            db,
            clinic_id=1,
            entity_type="patient",
            operation="create",
            payload={"id": 1},
            entity_uid="1",
            client_request_id="req-1",
        )
        assert a.event_id == b.event_id
        assert db.query(SyncOutboxEvent).count() == 1

    def test_local_mirror_push_and_ingest(self, db, monkeypatch):
        monkeypatch.setenv("CLINIC_NODE_SYNC_LOCAL_MIRROR", "true")
        monkeypatch.delenv("CLOUD_SYNC_URL", raising=False)
        enqueue_outbox_event(
            db,
            clinic_id=1,
            entity_type="patient",
            operation="create",
            payload={"id": 9},
            entity_uid="9",
            client_request_id="req-push",
        )
        result = push_pending_to_cloud(db, clinic_id=1)
        assert result["pushed"] >= 1
        assert result["failed"] == 0


class TestConflicts:
    def test_resolve_merge_and_manual(self, db):
        c = record_conflict(
            db,
            clinic_id=1,
            entity_type="stock_movement",
            entity_uid="m1",
            local_payload={"qty": 5, "note": "local"},
            remote_payload={"qty": 7, "loc": "A"},
            local_version=1,
            remote_version=2,
        )
        resolved = resolve_conflict(
            db, conflict_id=c.id, clinic_id=1, policy="merge", resolved_by_user_id=1
        )
        assert resolved.status == "resolved"
        merged = json.loads(resolved.merged_json)
        assert merged["qty"] == 7
        assert merged.get("note") == "local" or merged.get("_local_note") or "note" in merged

        c2 = record_conflict(
            db,
            clinic_id=1,
            entity_type="patient",
            entity_uid="p1",
            local_payload={"name": "A"},
            remote_payload={"name": "B"},
        )
        r2 = resolve_conflict(
            db,
            conflict_id=c2.id,
            clinic_id=1,
            policy="manual",
            manual_payload={"name": "C"},
            note="clinician chose C",
        )
        assert json.loads(r2.merged_json)["name"] == "C"
