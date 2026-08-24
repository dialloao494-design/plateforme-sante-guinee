"""Safe staff invitation and single-use account activation."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import models
from core.frontend_url import resolve_frontend_url
from security import hash_password, validate_password
from services.email_service import send_staff_activation_email
from services.user_provisioning import create_staff_user

ACTIVATION_HOURS = 48


class ActivationError(ValueError):
    pass


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue(db: Session, *, user: models.User, actor_id: int) -> tuple[models.StaffActivationToken, str]:
    now = datetime.utcnow()
    db.query(models.StaffActivationToken).filter(
        models.StaffActivationToken.user_id == user.id,
        models.StaffActivationToken.used_at.is_(None),
        models.StaffActivationToken.revoked_at.is_(None),
    ).update({"revoked_at": now}, synchronize_session=False)
    raw = secrets.token_urlsafe(32)
    row = models.StaffActivationToken(
        user_id=user.id,
        created_by_user_id=actor_id,
        token_hash=_digest(raw),
        expires_at=now + timedelta(hours=ACTIVATION_HOURS),
        delivery_status="pending",
    )
    db.add(row)
    db.flush()
    return row, raw


def _deliver(db: Session, *, row: models.StaffActivationToken, user: models.User, raw: str) -> bool:
    link = f"{resolve_frontend_url()}/activate-staff?token={raw}"
    clinic = db.query(models.Clinic).filter(models.Clinic.id == user.clinic_id).first()
    sent = send_staff_activation_email(
        user.email,
        link,
        clinic_name=clinic.name if clinic else "votre clinique",
        first_name=user.first_name,
    )
    row.delivery_attempts = int(row.delivery_attempts or 0) + 1
    row.last_sent_at = datetime.utcnow()
    row.delivery_status = "sent" if sent else "failed"
    db.commit()
    db.refresh(row)
    return sent


def invite_staff(db: Session, *, actor_id: int, clinic_id: int, email: str, role: str, first_name: str, last_name: str):
    # The random internal secret is never returned or communicated. Login remains
    # impossible because both the user and clinic membership start inactive.
    provisioned = create_staff_user(
        db,
        email=email,
        password=f"Invite-{secrets.token_urlsafe(24)}-9a!",
        role=role,
        clinic_id=clinic_id,
        actor_user_id=actor_id,
        first_name=first_name,
        last_name=last_name,
        active=False,
        email_verified=False,
    )
    row, raw = _issue(db, user=provisioned.user, actor_id=actor_id)
    db.commit()
    sent = _deliver(db, row=row, user=provisioned.user, raw=raw)
    return provisioned.user, row, sent


def resend_invitation(db: Session, *, actor_id: int, user: models.User):
    if user.is_active:
        raise ActivationError("Ce compte est déjà activé.")
    row, raw = _issue(db, user=user, actor_id=actor_id)
    db.commit()
    sent = _deliver(db, row=row, user=user, raw=raw)
    return row, sent


def inspect_activation(db: Session, token: str) -> dict:
    row = db.query(models.StaffActivationToken).filter(models.StaffActivationToken.token_hash == _digest(token)).first()
    now = datetime.utcnow()
    if not row or row.used_at or row.revoked_at or row.expires_at <= now:
        raise ActivationError("Cette invitation est invalide ou a expiré.")
    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user or user.is_active:
        raise ActivationError("Cette invitation n'est plus utilisable.")
    clinic = db.query(models.Clinic).filter(models.Clinic.id == user.clinic_id).first()
    local, _, domain = user.email.partition("@")
    masked = f"{local[:2]}***@{domain}" if domain else "***"
    return {
        "email_masked": masked,
        "first_name": user.first_name,
        "clinic_name": clinic.name if clinic else "Clinique",
        "expires_at": row.expires_at,
    }


def complete_activation(db: Session, *, token: str, password: str) -> models.User:
    validate_password(password)
    row = db.query(models.StaffActivationToken).filter(models.StaffActivationToken.token_hash == _digest(token)).with_for_update().first()
    now = datetime.utcnow()
    if not row or row.used_at or row.revoked_at or row.expires_at <= now:
        raise ActivationError("Cette invitation est invalide ou a expiré.")
    user = db.query(models.User).filter(models.User.id == row.user_id).with_for_update().first()
    if not user or user.is_active:
        raise ActivationError("Cette invitation n'est plus utilisable.")
    membership = db.query(models.ClinicStaff).filter(
        models.ClinicStaff.user_id == user.id,
        models.ClinicStaff.clinic_id == user.clinic_id,
    ).first()
    user.hashed_password = hash_password(password)
    user.is_active = True
    user.email_verified_at = now
    user.must_change_password = False
    user.session_version = int(user.session_version or 0) + 1
    user.token_version = int(user.token_version or 0) + 1
    if membership:
        membership.is_active = True
    row.used_at = now
    db.commit()
    db.refresh(user)
    return user
