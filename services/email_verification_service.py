"""Email verification tokens for public registration."""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from services.email_service import send_email_verification_email

logger = logging.getLogger(__name__)

VERIFY_TOKEN_HOURS = int(os.getenv("EMAIL_VERIFY_TOKEN_HOURS", "48"))


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_verify_link(raw_token: str) -> str:
    frontend = (os.getenv("FRONTEND_URL") or os.getenv("PUBLIC_FRONTEND_URL") or "").rstrip("/")
    if not frontend:
        frontend = "http://localhost:5173"
    return f"{frontend}/verify-email?token={raw_token}"


def create_verification_token(db: Session, *, user_id: int) -> str:
    raw = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw)
    expires = datetime.utcnow() + timedelta(hours=VERIFY_TOKEN_HOURS)

    db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.user_id == user_id,
        models.EmailVerificationToken.used_at.is_(None),
    ).update({"used_at": datetime.utcnow()})

    db.add(
        models.EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
        )
    )
    db.commit()
    return raw


def send_verification_email(db: Session, *, user: models.User) -> bool:
    if user.email_verified_at:
        return True
    raw = create_verification_token(db, user_id=user.id)
    link = build_verify_link(raw)
    sent = send_email_verification_email(user.email, link)
    if not sent:
        logger.info("Email verification link for %s (email not configured): %s", user.email, link)
    return sent


def verify_email_with_token(db: Session, *, raw_token: str) -> bool:
    token_hash = _hash_token(raw_token)
    row = (
        db.query(models.EmailVerificationToken)
        .filter(
            models.EmailVerificationToken.token_hash == token_hash,
            models.EmailVerificationToken.used_at.is_(None),
            models.EmailVerificationToken.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if not row:
        return False

    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user:
        return False

    now = datetime.utcnow()
    user.email_verified_at = now
    row.used_at = now
    db.add(user)
    db.add(row)
    db.commit()
    return True


def resend_verification(db: Session, *, email: str) -> None:
    normalized = email.lower().strip()
    user = db.query(models.User).filter(func.lower(models.User.email) == normalized).first()
    if not user or user.email_verified_at:
        return
    send_verification_email(db, user=user)
