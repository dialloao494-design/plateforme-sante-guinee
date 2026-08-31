"""Refresh-token lifecycle, lockout, and access-token denylist (Security Wave 0)."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from models.refresh_token import AccessTokenDenylist, RefreshToken
from models.user import User

logger = logging.getLogger(__name__)

REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
LOGIN_SOFT_LOCK_START = int(os.getenv("LOGIN_SOFT_LOCK_START", "3"))


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_refresh_token(
    db: Session,
    *,
    user: User,
    family_id: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, RefreshToken]:
    """Create a rotating refresh token; returns (raw_token, row)."""
    raw = secrets.token_urlsafe(48)
    jti = str(uuid.uuid4())
    family = family_id or str(uuid.uuid4())
    row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        jti=jti,
        family_id=family,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=(user_agent or "")[:512] or None,
        ip_address=(ip_address or "")[:64] or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return raw, row


def rotate_refresh_token(
    db: Session,
    *,
    raw_token: str,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, str, RefreshToken]:
    """
    Validate and rotate a refresh token.
    Reuse of a revoked family token revokes the entire family (theft detection).

    Uses compare-and-set revoke so concurrent refresh of the same token cannot
    mint two live chains (second writer is treated as reuse).
    """
    token_hash = _hash_token(raw_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if row.revoked_at is not None:
        # Possible token theft — revoke family
        _revoke_family(db, family_id=row.family_id, reason="reuse")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected; session revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if row.expires_at <= datetime.utcnow():
        row.revoked_at = datetime.utcnow()
        db.add(row)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or (hasattr(user, "is_active") and user.is_active is False):
        _revoke_family(db, family_id=row.family_id, reason="inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    now = datetime.utcnow()
    claimed = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.id == row.id,
            RefreshToken.revoked_at.is_(None),
        )
        .update(
            {RefreshToken.revoked_at: now},
            synchronize_session=False,
        )
    )
    if claimed != 1:
        db.rollback()
        reuse = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if reuse is not None:
            _revoke_family(db, family_id=reuse.family_id, reason="reuse")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected; session revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue replacement in the same transaction (do not call issue_refresh_token —
    # that commits early and re-opens a race window).
    raw_new = secrets.token_urlsafe(48)
    new_jti = str(uuid.uuid4())
    new_row = RefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_new),
        jti=new_jti,
        family_id=row.family_id,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=(user_agent or row.user_agent or "")[:512] or None,
        ip_address=(ip_address or row.ip_address or "")[:64] or None,
    )
    db.add(new_row)
    db.flush()
    # Persist replaced_by on the revoked row
    db.query(RefreshToken).filter(RefreshToken.id == row.id).update(
        {RefreshToken.replaced_by_jti: new_jti},
        synchronize_session=False,
    )
    db.commit()
    db.refresh(new_row)
    return user, raw_new, new_row


def revoke_refresh_token(db: Session, *, raw_token: str | None) -> None:
    if not raw_token:
        return
    token_hash = _hash_token(raw_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not row:
        return
    _revoke_family(db, family_id=row.family_id, reason="logout")


def revoke_all_user_refresh_tokens(db: Session, *, user_id: int, commit: bool = True) -> int:
    now = datetime.utcnow()
    rows = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    for row in rows:
        row.revoked_at = now
        db.add(row)
    if commit:
        db.commit()
    else:
        db.flush()
    return len(rows)


def _revoke_family(db: Session, *, family_id: str, reason: str) -> None:
    now = datetime.utcnow()
    rows = (
        db.query(RefreshToken)
        .filter(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    for row in rows:
        row.revoked_at = now
        db.add(row)
    db.commit()
    logger.info("Revoked refresh family=%s reason=%s count=%s", family_id, reason, len(rows))


def denylist_access_jti(
    db: Session,
    *,
    jti: str,
    user_id: int | None,
    expires_at: datetime,
    reason: str = "logout",
) -> None:
    if not jti:
        return
    existing = db.query(AccessTokenDenylist).filter(AccessTokenDenylist.jti == jti).first()
    if existing:
        return
    db.add(
        AccessTokenDenylist(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            reason=reason,
        )
    )
    db.commit()


def is_access_jti_denied(db: Session, *, jti: str | None) -> bool:
    if not jti:
        return False
    row = (
        db.query(AccessTokenDenylist)
        .filter(
            AccessTokenDenylist.jti == jti,
            AccessTokenDenylist.expires_at > datetime.utcnow(),
        )
        .first()
    )
    return row is not None


def check_account_lockout(user: User) -> None:
    locked_until = getattr(user, "locked_until", None)
    if locked_until and locked_until > datetime.utcnow():
        retry_after = int((locked_until - datetime.utcnow()).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to failed login attempts. Try again later.",
            headers={"Retry-After": str(max(retry_after, 1))},
        )


def record_login_failure(db: Session, user: User | None) -> None:
    if user is None:
        return
    failures = int(getattr(user, "failed_login_attempts", 0) or 0) + 1
    user.failed_login_attempts = failures
    now = datetime.utcnow()
    if failures >= LOGIN_MAX_FAILURES:
        user.locked_until = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        db.add(user)
        db.commit()
        logger.warning("Account locked user_id=%s failures=%s", user.id, failures)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to failed login attempts. Try again later.",
            headers={"Retry-After": str(LOGIN_LOCKOUT_MINUTES * 60)},
        )
    db.add(user)
    db.commit()
    if failures >= LOGIN_SOFT_LOCK_START:
        delay = min(2**failures, 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Slow down and try again.",
            headers={"Retry-After": str(delay)},
        )


def record_login_success(db: Session, user: User) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    db.add(user)
    db.commit()


def bump_token_version(db: Session, user: User) -> None:
    """Invalidate all outstanding access tokens by bumping token_version."""
    current = int(getattr(user, "token_version", 0) or 0)
    user.token_version = current + 1
    user.password_changed_at = datetime.utcnow()
    db.add(user)
    revoke_all_user_refresh_tokens(db, user_id=user.id)


def client_meta(request: Any) -> tuple[str | None, str | None]:
    ua = None
    ip = None
    try:
        ua = request.headers.get("user-agent")
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        elif request.client:
            ip = request.client.host
    except Exception:
        pass
    return ua, ip
