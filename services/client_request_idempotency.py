"""Lookup/store helpers for X-Client-Request-Id idempotency."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)

IDEMPOTENCY_HEADER = "X-Client-Request-Id"


def hash_request_body(body: bytes | str | None) -> str:
    raw = body if isinstance(body, (bytes, bytearray)) else (body or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def hash_json_payload(payload: Any) -> str:
    try:
        raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        raw = str(payload)
    return hash_request_body(raw)


def find_idempotent_response(
    db: Session,
    *,
    client_request_id: str,
    request_hash: str,
) -> models.ApiClientIdempotencyKey | None:
    row = (
        db.query(models.ApiClientIdempotencyKey)
        .filter(models.ApiClientIdempotencyKey.client_request_id == client_request_id)
        .first()
    )
    if not row:
        return None
    if row.request_hash != request_hash:
        return row  # caller treats hash mismatch as conflict
    return row


def store_idempotent_response(
    db: Session,
    *,
    client_request_id: str,
    method: str,
    path: str,
    request_hash: str,
    status_code: int,
    response_body: str,
    user_id: int | None = None,
    clinic_id: int | None = None,
) -> models.ApiClientIdempotencyKey | None:
    row = models.ApiClientIdempotencyKey(
        client_request_id=client_request_id[:128],
        method=method.upper()[:16],
        path=path[:512],
        request_hash=request_hash,
        user_id=user_id,
        clinic_id=clinic_id,
        status_code=int(status_code),
        response_body=response_body or "",
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(models.ApiClientIdempotencyKey)
            .filter(models.ApiClientIdempotencyKey.client_request_id == client_request_id)
            .first()
        )
        logger.info("Idempotency key race for %s — returning existing row", client_request_id)
        return existing
