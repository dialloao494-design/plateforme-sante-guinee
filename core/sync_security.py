"""
Sync / delta-sync security helpers — Security Wave 5.

Provides HMAC-signed envelopes, replay protection (nonce + timestamp skew),
and integrity hashing for outbox/ingest without enabling Offline V1 product APIs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable


DEFAULT_MAX_SKEW_SECONDS = int(os.getenv("SYNC_MAX_SKEW_SECONDS", "300"))
DEFAULT_NONCE_TTL_SECONDS = int(os.getenv("SYNC_NONCE_TTL_SECONDS", "600"))


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hmac_sha256_hex(secret: str | bytes, data: bytes) -> str:
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def verify_hmac_sha256(secret: str | bytes, data: bytes, signature_hex: str) -> bool:
    expected = hmac_sha256_hex(secret, data)
    return hmac.compare_digest(expected, (signature_hex or "").strip())


@dataclass(frozen=True)
class SignedSyncEnvelope:
    event_id: str
    clinic_id: int
    entity_type: str
    operation: str
    payload: dict[str, Any]
    record_version: int
    timestamp: int
    nonce: str
    content_sha256: str
    signature: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "clinic_id": self.clinic_id,
            "entity_type": self.entity_type,
            "operation": self.operation,
            "payload": self.payload,
            "record_version": self.record_version,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "content_sha256": self.content_sha256,
            "signature": self.signature,
        }


def build_signed_envelope(
    *,
    secret: str,
    event_id: str,
    clinic_id: int,
    entity_type: str,
    operation: str,
    payload: dict[str, Any],
    record_version: int = 1,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> SignedSyncEnvelope:
    """Create a delta-sync envelope with content hash + HMAC signature."""
    ts = int(timestamp if timestamp is not None else time.time())
    nonce_val = nonce or secrets.token_urlsafe(16)
    body = {
        "event_id": event_id,
        "clinic_id": clinic_id,
        "entity_type": entity_type,
        "operation": operation,
        "payload": payload,
        "record_version": record_version,
        "timestamp": ts,
        "nonce": nonce_val,
    }
    content_hash = sha256_hex(canonical_json(body))
    body_with_hash = {**body, "content_sha256": content_hash}
    signature = hmac_sha256_hex(secret, canonical_json(body_with_hash))
    return SignedSyncEnvelope(
        event_id=event_id,
        clinic_id=clinic_id,
        entity_type=entity_type,
        operation=operation,
        payload=payload,
        record_version=record_version,
        timestamp=ts,
        nonce=nonce_val,
        content_sha256=content_hash,
        signature=signature,
    )


def verify_signed_envelope(
    envelope: dict[str, Any],
    *,
    secret: str,
    max_skew_seconds: int = DEFAULT_MAX_SKEW_SECONDS,
    now: int | None = None,
) -> tuple[bool, str]:
    """
    Verify integrity + authenticity of a sync envelope.
    Does not consume nonces — call ReplayGuard.consume after success.
    """
    required = (
        "event_id",
        "clinic_id",
        "entity_type",
        "operation",
        "payload",
        "record_version",
        "timestamp",
        "nonce",
        "content_sha256",
        "signature",
    )
    for key in required:
        if key not in envelope:
            return False, f"missing_field:{key}"

    body = {
        "event_id": envelope["event_id"],
        "clinic_id": envelope["clinic_id"],
        "entity_type": envelope["entity_type"],
        "operation": envelope["operation"],
        "payload": envelope["payload"],
        "record_version": envelope["record_version"],
        "timestamp": envelope["timestamp"],
        "nonce": envelope["nonce"],
    }
    expected_hash = sha256_hex(canonical_json(body))
    if not hmac.compare_digest(expected_hash, str(envelope["content_sha256"])):
        return False, "content_sha256_mismatch"

    body_with_hash = {**body, "content_sha256": envelope["content_sha256"]}
    if not verify_hmac_sha256(secret, canonical_json(body_with_hash), str(envelope["signature"])):
        return False, "signature_invalid"

    current = int(now if now is not None else time.time())
    try:
        ts = int(envelope["timestamp"])
    except (TypeError, ValueError):
        return False, "timestamp_invalid"
    if abs(current - ts) > max_skew_seconds:
        return False, "timestamp_skew"

    return True, "ok"


class ReplayGuard:
    """
    In-memory nonce / event_id replay protection with TTL.
    Process-local; suitable for unit tests and single-node ingest.
    """

    def __init__(self, *, ttl_seconds: int = DEFAULT_NONCE_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def _purge(self, now: float) -> None:
        expired = [k for k, exp in self._seen.items() if exp <= now]
        for k in expired:
            del self._seen[k]

    def seen(self, key: str, *, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        with self._lock:
            self._purge(current)
            return key in self._seen

    def consume(self, key: str, *, now: float | None = None) -> bool:
        """
        Mark key as seen. Returns False if already consumed (replay).
        """
        current = time.time() if now is None else now
        with self._lock:
            self._purge(current)
            if key in self._seen:
                return False
            self._seen[key] = current + self.ttl_seconds
            return True

    def consume_envelope(self, envelope: dict[str, Any]) -> tuple[bool, str]:
        nonce = str(envelope.get("nonce") or "")
        event_id = str(envelope.get("event_id") or "")
        if not nonce or not event_id:
            return False, "missing_nonce_or_event_id"
        if not self.consume(f"nonce:{nonce}"):
            return False, "replay_nonce"
        if not self.consume(f"event:{event_id}"):
            return False, "replay_event_id"
        return True, "ok"


def require_sync_token(provided: str | None, expected: str | None) -> tuple[bool, str]:
    """Gate ingest with shared X-Sync-Token when configured."""
    expected_clean = (expected or "").strip()
    if not expected_clean:
        return False, "sync_token_not_configured"
    if not provided or not hmac.compare_digest(provided.strip(), expected_clean):
        return False, "sync_token_invalid"
    return True, "ok"


def delta_batch_integrity(envelopes: Iterable[dict[str, Any]]) -> str:
    """Hash an ordered batch of envelopes for multi-event delta integrity."""
    parts = [canonical_json(env) for env in envelopes]
    return sha256_hex(b"\n".join(parts))
