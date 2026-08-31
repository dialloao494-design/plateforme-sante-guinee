"""One tenant-safe staff lifecycle used by clinic and platform administrators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from models.refresh_token import AccessTokenDenylist, RefreshToken
from services.auth_session_service import revoke_all_user_refresh_tokens
from services.clinical_audit_service import ClinicalAuditService


@dataclass
class StaffLifecycleError(Exception):
    message: str
    status_code: int = 409

    def __str__(self) -> str:
        return self.message


def _staff(db: Session, clinic_id: int, user_id: int) -> models.User:
    membership_ids = db.query(models.ClinicStaff.user_id).filter(models.ClinicStaff.clinic_id == clinic_id)
    user = db.query(models.User).filter(
        models.User.id == user_id,
        or_(models.User.clinic_id == clinic_id, models.User.id.in_(membership_ids)),
    ).first()
    if not user:
        raise StaffLifecycleError("Membre du personnel introuvable.", 404)
    if user.role in ("platform_owner", "platform_admin", "patient"):
        raise StaffLifecycleError("Ce compte n’est pas un membre du personnel de cette clinique.", 400)
    return user


def _snapshot(user: models.User) -> dict:
    return {"id": user.id, "email": user.email, "role": user.role, "is_active": bool(user.is_active)}


def _audit(db: Session, *, actor, target, clinic_id: int, action: str, reason: str, ip: str | None, user_agent: str | None, before: dict, after: dict | None) -> None:
    ClinicalAuditService.log(
        db, actor=actor, patient_id=None, clinic_id=clinic_id, action=action,
        resource_type="staff", resource_id=target.id, client_ip=ip,
        user_agent=user_agent, reason=reason, before=before, after=after, commit=False,
    )


def deactivate_staff(db: Session, *, clinic_id: int, user_id: int, actor, reason: str, ip: str | None = None, user_agent: str | None = None) -> models.User:
    user = _staff(db, clinic_id, user_id)
    if user.id == actor.id:
        raise StaffLifecycleError("Vous ne pouvez pas désactiver votre propre compte.", 400)
    if not reason.strip():
        raise StaffLifecycleError("Indiquez la raison de la désactivation.", 422)
    if user.role in ("clinic_admin", "admin") and user.is_active:
        remaining = db.query(models.User).filter(
            models.User.clinic_id == clinic_id,
            models.User.role.in_(("clinic_admin", "admin")),
            models.User.is_active.is_(True),
            models.User.id != user.id,
        ).count()
        if remaining == 0:
            raise StaffLifecycleError("La clinique doit conserver au moins un administrateur actif.")
    before = _snapshot(user)
    user.is_active = False
    user.session_version = int(user.session_version or 0) + 1
    user.token_version = int(user.token_version or 0) + 1
    revoke_all_user_refresh_tokens(db, user_id=user.id, commit=False)
    db.query(models.ClinicStaff).filter(
        models.ClinicStaff.clinic_id == clinic_id, models.ClinicStaff.user_id == user.id,
    ).update({models.ClinicStaff.is_active: False}, synchronize_session=False)
    _audit(db, actor=actor, target=user, clinic_id=clinic_id, action="deactivate", reason=reason, ip=ip, user_agent=user_agent, before=before, after=_snapshot(user))
    db.commit(); db.refresh(user)
    return user


def reactivate_staff(db: Session, *, clinic_id: int, user_id: int, actor, reason: str, ip: str | None = None, user_agent: str | None = None) -> models.User:
    user = _staff(db, clinic_id, user_id)
    if not reason.strip():
        raise StaffLifecycleError("Indiquez la raison de la réactivation.", 422)
    pending = db.query(models.StaffActivationToken).filter(
        models.StaffActivationToken.user_id == user.id,
        models.StaffActivationToken.used_at.is_(None),
        models.StaffActivationToken.revoked_at.is_(None),
    ).first()
    if user.email_verified_at is None and user.last_login_at is None and pending:
        raise StaffLifecycleError("Ce compte n’a jamais été activé. Renvoyez plutôt son invitation.")
    before = _snapshot(user)
    user.is_active = True
    user.failed_login_attempts = 0
    user.locked_until = None
    user.session_version = int(user.session_version or 0) + 1
    user.token_version = int(user.token_version or 0) + 1
    db.query(models.ClinicStaff).filter(
        models.ClinicStaff.clinic_id == clinic_id, models.ClinicStaff.user_id == user.id,
    ).update({models.ClinicStaff.is_active: True}, synchronize_session=False)
    _audit(db, actor=actor, target=user, clinic_id=clinic_id, action="reactivate", reason=reason, ip=ip, user_agent=user_agent, before=before, after=_snapshot(user))
    db.commit(); db.refresh(user)
    return user


def delete_unused_staff(db: Session, *, clinic_id: int, user_id: int, actor, reason: str, ip: str | None = None, user_agent: str | None = None) -> None:
    user = _staff(db, clinic_id, user_id)
    if user.id == actor.id:
        raise StaffLifecycleError("Vous ne pouvez pas supprimer votre propre compte.", 400)
    if not reason.strip():
        raise StaffLifecycleError("Indiquez la raison de la suppression.", 422)
    if user.is_active:
        raise StaffLifecycleError("Désactivez d’abord ce compte.")
    pending = db.query(models.StaffActivationToken).filter(
        models.StaffActivationToken.user_id == user.id,
        models.StaffActivationToken.used_at.is_(None),
    ).first()
    authored = db.query(models.ClinicalAuditLog.id).filter(models.ClinicalAuditLog.actor_id == user.id).first()
    if user.email_verified_at is not None or user.last_login_at is not None or not pending or authored:
        raise StaffLifecycleError("Ce compte possède un historique. Il doit rester désactivé afin de préserver la traçabilité clinique.")
    if db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first():
        raise StaffLifecycleError("Ce compte possède un profil médecin. Conservez-le désactivé.")
    before = _snapshot(user)
    target_id = user.id
    for model in (models.StaffActivationToken, models.PasswordResetToken, models.EmailVerificationToken, RefreshToken, AccessTokenDenylist, models.NotificationEvent):
        db.query(model).filter(model.user_id == target_id).delete(synchronize_session=False)
    db.query(models.ClinicStaff).filter(models.ClinicStaff.clinic_id == clinic_id, models.ClinicStaff.user_id == target_id).delete(synchronize_session=False)
    db.delete(user); db.flush()
    ClinicalAuditService.log(
        db, actor=actor, patient_id=None, clinic_id=clinic_id, action="delete_unused",
        resource_type="staff", resource_id=target_id, client_ip=ip, user_agent=user_agent,
        reason=reason, before=before, after=None, commit=False,
    )
    db.commit()


def revoke_sessions(db: Session, *, clinic_id: int, user_id: int, actor, reason: str, ip: str | None = None, user_agent: str | None = None) -> int:
    user = _staff(db, clinic_id, user_id)
    if not reason.strip():
        raise StaffLifecycleError("Indiquez la raison de la déconnexion.", 422)
    before = _snapshot(user)
    count = revoke_all_user_refresh_tokens(db, user_id=user.id, commit=False)
    user.session_version = int(user.session_version or 0) + 1
    user.token_version = int(user.token_version or 0) + 1
    _audit(db, actor=actor, target=user, clinic_id=clinic_id, action="revoke_sessions", reason=reason, ip=ip, user_agent=user_agent, before=before, after={**before, "revoked_sessions": count})
    db.commit()
    return count
