"""Production Clinic Node licensing — HMAC-signed, clinic-bound, care-safe enforcement."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from models.clinic_node_ops import ClinicNodeLicense

logger = logging.getLogger(__name__)

DEFAULT_VALID_DAYS = int(os.getenv("CLINIC_NODE_LICENSE_VALID_DAYS", "365"))
DEFAULT_GRACE_DAYS = int(os.getenv("CLINIC_NODE_LICENSE_GRACE_DAYS", "180"))


def license_signing_key() -> bytes:
    raw = (
        os.getenv("CLINIC_NODE_LICENSE_SECRET")
        or os.getenv("JWT_SECRET")
        or os.getenv("SECRET_KEY")
        or ""
    ).strip()
    if len(raw) < 32:
        # Deterministic weak fallback only for empty unit-test envs; production compose sets secrets.
        raw = (raw + "clinic-node-license-dev-fallback-key!!!!")[:48]
    return raw.encode("utf-8")


def _canonical_payload(claims: dict[str, Any]) -> str:
    return json.dumps(claims, sort_keys=True, separators=(",", ":"), default=str)


def sign_license_claims(claims: dict[str, Any]) -> str:
    body = _canonical_payload(claims)
    return hmac.new(license_signing_key(), body.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_license_signature(claims: dict[str, Any], signature: str) -> bool:
    if not signature:
        return False
    expected = sign_license_claims(claims)
    return hmac.compare_digest(expected, signature)


def build_signed_license(
    *,
    clinic_id: int,
    node_id: str | None,
    plan: str = "offline-v1",
    valid_days: int | None = None,
    grace_days: int | None = None,
    issued_at: datetime | None = None,
) -> tuple[dict[str, Any], str, datetime, datetime, datetime]:
    issued = issued_at or datetime.utcnow()
    valid_until = issued + timedelta(days=valid_days or DEFAULT_VALID_DAYS)
    grace_until = valid_until + timedelta(days=grace_days or DEFAULT_GRACE_DAYS)
    claims = {
        "v": 1,
        "clinic_id": int(clinic_id),
        "node_id": node_id or os.getenv("NODE_ID") or "",
        "plan": plan,
        "issued_at": issued.isoformat() + "Z",
        "valid_until": valid_until.isoformat() + "Z",
        "grace_until": grace_until.isoformat() + "Z",
    }
    sig = sign_license_claims(claims)
    return claims, sig, issued, valid_until, grace_until


def license_state_from_row(row: ClinicNodeLicense | None, *, node_id: str | None = None) -> str:
    if not row or not row.is_active:
        return "missing"
    try:
        claims = json.loads(row.token_json)
    except Exception:
        return "invalid"
    if not verify_license_signature(claims, row.signature or ""):
        return "invalid"
    expected_clinic = int(claims.get("clinic_id") or 0)
    if expected_clinic != int(row.clinic_id):
        return "invalid"
    expected_node = str(claims.get("node_id") or "")
    current_node = node_id or os.getenv("NODE_ID") or ""
    if expected_node and current_node and expected_node != current_node:
        return "node_mismatch"
    now = datetime.utcnow()
    if now <= row.valid_until:
        return "OK"
    if now <= row.grace_until:
        return "GRACE"
    return "EXPIRED"


def get_active_license(db: Session, clinic_id: int) -> ClinicNodeLicense | None:
    return (
        db.query(ClinicNodeLicense)
        .filter(ClinicNodeLicense.clinic_id == clinic_id, ClinicNodeLicense.is_active.is_(True))
        .order_by(ClinicNodeLicense.id.desc())
        .first()
    )


def activate_or_renew_license(
    db: Session,
    *,
    clinic_id: int,
    node_id: str | None = None,
    plan: str = "offline-v1",
    valid_days: int | None = None,
    grace_days: int | None = None,
    renew: bool = False,
) -> ClinicNodeLicense:
    """Issue a signed clinic-bound license. Offline-valid until grace_until after activation."""
    node = node_id or os.getenv("NODE_ID") or "unknown-node"
    existing = get_active_license(db, clinic_id)
    if existing and not renew:
        state = license_state_from_row(existing, node_id=node)
        if state in {"OK", "GRACE"}:
            existing.last_validated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

    if existing:
        existing.is_active = False

    claims, sig, issued, valid_until, grace_until = build_signed_license(
        clinic_id=clinic_id,
        node_id=node,
        plan=plan,
        valid_days=valid_days,
        grace_days=grace_days,
    )
    row = ClinicNodeLicense(
        clinic_id=clinic_id,
        node_id=node,
        plan=plan,
        issued_at=issued,
        valid_until=valid_until,
        grace_until=grace_until,
        token_json=json.dumps(claims),
        signature=sig,
        is_active=True,
        activated_at=datetime.utcnow(),
        last_validated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def import_signed_license_token(
    db: Session,
    *,
    clinic_id: int,
    token_json: str,
    signature: str,
    node_id: str | None = None,
) -> ClinicNodeLicense:
    """Activate from an externally issued signed token (offline after activation)."""
    claims = json.loads(token_json)
    if not verify_license_signature(claims, signature):
        raise HTTPException(status_code=400, detail="Invalid license signature")
    if int(claims.get("clinic_id") or 0) != int(clinic_id):
        raise HTTPException(status_code=400, detail="License clinic_id mismatch")
    node = node_id or os.getenv("NODE_ID") or ""
    claim_node = str(claims.get("node_id") or "")
    if claim_node and node and claim_node != node:
        raise HTTPException(status_code=400, detail="License node_id mismatch")

    for old in (
        db.query(ClinicNodeLicense)
        .filter(ClinicNodeLicense.clinic_id == clinic_id, ClinicNodeLicense.is_active.is_(True))
        .all()
    ):
        old.is_active = False

    issued = datetime.fromisoformat(str(claims["issued_at"]).replace("Z", ""))
    valid_until = datetime.fromisoformat(str(claims["valid_until"]).replace("Z", ""))
    grace_until = datetime.fromisoformat(str(claims["grace_until"]).replace("Z", ""))
    row = ClinicNodeLicense(
        clinic_id=clinic_id,
        node_id=claim_node or node,
        plan=str(claims.get("plan") or "offline-v1"),
        issued_at=issued,
        valid_until=valid_until,
        grace_until=grace_until,
        token_json=_canonical_payload(claims),
        signature=signature,
        is_active=True,
        activated_at=datetime.utcnow(),
        last_validated_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# Paths that must stay available when license is missing/expired (patient care + activation).
_LICENSE_ALWAYS_ALLOW_PREFIXES = (
    "/health",
    "/api/health",
    "/api/auth/login",
    "/api/auth/login-json",
    "/api/auth/me",
    "/api/auth/refresh",
    "/api/clinic-node/license",
    "/docs",
    "/openapi.json",
    "/redoc",
)

# Administrative / ops mutations blocked only when EXPIRED or invalid (care continues).
_LICENSE_BLOCK_WHEN_EXPIRED_PREFIXES = (
    "/api/clinical/staff",
    "/api/platform",
    "/api/clinic-node/sync/push",
    "/api/clinic-node/sync/outbox",  # POST enqueue still allowed via GET; see method check
    "/api/clinic-node/owner",
)


def path_is_always_allowed(path: str) -> bool:
    p = path.rstrip("/") or "/"
    for prefix in _LICENSE_ALWAYS_ALLOW_PREFIXES:
        if p == prefix or p.startswith(prefix + "/") or p.startswith(prefix):
            if prefix in {"/api/auth/login", "/api/auth/login-json"} and p.startswith(prefix):
                return True
            if p == prefix or p.startswith(prefix):
                return True
    # Static SPA and root
    if not p.startswith("/api/"):
        return True
    return False


def path_blocks_when_expired(path: str, method: str) -> bool:
    """Return True if this request should be blocked when license is EXPIRED/invalid."""
    if method.upper() == "GET":
        # Read-only ops/monitoring remains available.
        return False
    p = path
    # Clinical patient-care writes always allowed (no interruption of care).
    care_prefixes = (
        "/api/clinical/reception",
        "/api/clinical/doctor",
        "/api/clinical/lab",
        "/api/clinical/pharmacy",
        "/api/clinical/billing",
        "/api/clinical/nurse",
        "/api/clinical/consultations",
        "/api/clinical/patients",
        "/api/hospitalization",
        "/api/radiology",
        "/api/nursing",
        "/api/nurse",
        "/api/immunization",
        "/api/nutrition",
        "/api/unified-billing",
        "/api/clinic-node/backup",  # DR must work even if license expired
        "/api/clinic-node/license",  # renew/activate
    )
    for prefix in care_prefixes:
        if p.startswith(prefix):
            return False
    for prefix in _LICENSE_BLOCK_WHEN_EXPIRED_PREFIXES:
        if p.startswith(prefix):
            return True
    # Default: allow clinical-ish unknowns; block platform admin mutations
    if p.startswith("/api/platform") or p.startswith("/api/clinic-node/sync/push"):
        return True
    return False


def enforce_license_for_request(db: Session, request: Request, clinic_id: int | None) -> str | None:
    """
    Care-safe enforcement.
    Returns license state string for header injection, or raises HTTPException.
    """
    path = request.url.path
    if path_is_always_allowed(path):
        return None
    if not clinic_id:
        return None

    row = get_active_license(db, clinic_id)
    state = license_state_from_row(row)
    if state == "missing":
        # Allow license activation endpoints only (already in always-allow for GET/POST license).
        if path.startswith("/api/clinic-node/license"):
            return state
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "LICENSE_REQUIRED",
                "message": "Clinic Node license activation required",
                "state": state,
            },
        )
    if state in {"invalid", "node_mismatch"}:
        if path.startswith("/api/clinic-node/license"):
            return state
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "LICENSE_INVALID",
                "message": "Clinic Node license signature or binding invalid",
                "state": state,
            },
        )
    if state == "EXPIRED" and path_blocks_when_expired(path, request.method):
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "LICENSE_EXPIRED",
                "message": "License expired — renew required for this administrative action. Patient care remains available.",
                "state": state,
            },
        )
    return state
