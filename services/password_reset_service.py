"""Password reset token issuance and validation."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from security import hash_password

logger = logging.getLogger(__name__)

RESET_TOKEN_HOURS = int(os.getenv("PASSWORD_RESET_TOKEN_HOURS", "2"))


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_reset_token(db: Session, *, email: str) -> str | None:
    """Create reset token for user; returns raw token or None if email unknown."""
    normalized = email.lower().strip()
    user = db.query(models.User).filter(func.lower(models.User.email) == normalized).first()
    if not user or user.is_active is False:
        return None

    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires = datetime.utcnow() + timedelta(hours=RESET_TOKEN_HOURS)

    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.used_at.is_(None),
    ).update({"used_at": datetime.utcnow()})

    db.add(
        models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires,
        )
    )
    db.commit()
    return raw


def reset_password_with_token(db: Session, *, raw_token: str, new_password: str) -> bool:
    token_hash = _hash_token(raw_token)
    row = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.token_hash == token_hash,
            models.PasswordResetToken.used_at.is_(None),
            models.PasswordResetToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not row:
        return False

    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user:
        return False

    user.hashed_password = hash_password(new_password)
    if hasattr(user, "must_change_password"):
        user.must_change_password = False
    row.used_at = datetime.utcnow()
    db.add(user)
    db.add(row)
    db.commit()
    return True


def build_reset_link(raw_token: str) -> str:
    from core.frontend_url import resolve_frontend_url

    frontend = resolve_frontend_url()
    return f"{frontend}/reset-password?token={raw_token}"


def send_reset_email(email: str, raw_token: str) -> None:
    """Send password reset email via SMTP/Resend; log link when email is not configured."""
    from services.email_service import send_password_reset_email

    link = build_reset_link(raw_token)
    sent = send_password_reset_email(email, link)
    if not sent:
        logger.info("Password reset link for %s (email not configured): %s", email, link)
