"""
Single entry point for creating user accounts with enforced role policy.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from core.provisioning_context import provisioning_channel as authorized_channel
from core.roles import (
    CLINIC_ADMIN_ROLES,
    PRIVILEGED_ROLES,
    PublicRegistrationRoleError,
    PrivilegedRoleAssignmentError,
    assert_known_role,
    assert_public_registration_role,
    is_privileged_role,
)

# Re-export for API layers
__all__ = [
    "PublicRegistrationRoleError",
    "PrivilegedRoleAssignmentError",
    "EmailAlreadyRegisteredError",
    "register_public_user",
    "create_admin_user",
    "create_staff_user",
    "bootstrap_initial_admin",
    "bootstrap_platform_owner",
    "create_clinic_admin_user",
    "create_platform_owner_user",
    "platform_owner_exists",
    "setup_first_platform_owner",
    "PlatformOwnerSetupClosedError",
    "provision_cli_user",
    "ProvisionedUser",
]
from models.user import User
from security import hash_password, validate_password

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProvisionedUser:
    user: User
    doctor_id: int | None = None


class UserProvisioningError(Exception):
    """Base error for provisioning failures."""


class EmailAlreadyRegisteredError(UserProvisioningError):
    pass


class PlatformOwnerSetupClosedError(UserProvisioningError):
    """Raised when first-time owner setup is no longer available."""


PLATFORM_OWNER_CHANNELS = frozenset({"platform_owner_bootstrap", "platform_owner_setup"})


def _email_taken(db: Session, email: str) -> bool:
    normalized = email.lower().strip()
    return (
        db.query(User)
        .filter(func.lower(User.email) == normalized)
        .first()
        is not None
    )


def _ensure_patient_profile(db: Session, user: User) -> None:
    existing = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if existing:
        changed = False
        if existing.first_name is None:
            existing.first_name = "Patient"
            changed = True
        if existing.last_name is None:
            existing.last_name = f"User{user.id}"
            changed = True
        if existing.age is None:
            existing.age = 0
            changed = True
        if existing.gender is None:
            existing.gender = "unknown"
            changed = True
        if changed:
            db.commit()
        return
    db.add(
        models.Patient(
            user_id=user.id,
            first_name="Patient",
            last_name=f"User{user.id}",
            age=0,
            gender="unknown",
        )
    )
    db.commit()


def _ensure_doctor_profile(db: Session, user: User) -> models.Doctor:
    existing = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if existing:
        return existing
    doctor = models.Doctor(
        user_id=user.id,
        first_name="Doctor",
        last_name=f"User{user.id}",
        specialty="Médecine générale",
        city="Conakry · Kaloum",
        phone="000000000",
        photo_url=None,
        consultation_fee=0.0,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def _persist_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: str,
    channel: str,
) -> User:
    """
    Insert a user row after policy checks. Caller must handle IntegrityError → 409.
    """
    normalized_email = email.lower().strip()
    normalized_role = assert_known_role(role)

    if normalized_role == "platform_owner":
        if channel not in PLATFORM_OWNER_CHANNELS:
            raise PrivilegedRoleAssignmentError(
                "Platform owner accounts can only be created via secure bootstrap or setup."
            )
    elif is_privileged_role(normalized_role) and channel not in {
        "admin_api",
        "admin_bootstrap",
        "admin_cli",
        "test_fixture",
    }:
        raise PrivilegedRoleAssignmentError(
            f"Role '{normalized_role}' cannot be assigned via channel '{channel}'"
        )

    if _email_taken(db, normalized_email):
        raise EmailAlreadyRegisteredError(f"Email '{email}' is already registered.")

    with authorized_channel(channel):
        user = User(
            email=normalized_email,
            hashed_password=hash_password(password),
            role=normalized_role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if user.id is None:
        raise UserProvisioningError("User creation failed unexpectedly.")

    if normalized_role == "patient":
        _ensure_patient_profile(db, user)
    elif normalized_role == "doctor":
        _ensure_doctor_profile(db, user)

    logger.info(
        "Provisioned user id=%s role=%s channel=%s",
        user.id,
        user.role,
        channel,
    )
    return user


def register_public_user(db: Session, *, email: str, password: str, role: str) -> ProvisionedUser:
    """
    Public self-service registration (patient or doctor only).
    """
    try:
        validate_password(password)
    except ValueError as exc:
        raise UserProvisioningError(str(exc)) from exc

    public_role = assert_public_registration_role(role)
    try:
        user = _persist_user(
            db,
            email=email,
            password=password,
            role=public_role,
            channel="public_register",
        )
    except IntegrityError as exc:
        db.rollback()
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            raise EmailAlreadyRegisteredError("Email already registered") from exc
        raise UserProvisioningError("Error creating user.") from exc

    doctor_id = None
    if user.role == "doctor":
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if doc:
            doctor_id = doc.id
    return ProvisionedUser(user=user, doctor_id=doctor_id)


def create_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
    clinic_id: int | None = None,
    channel: str = "admin_api",
    actor_user_id: int | None = None,
) -> ProvisionedUser:
    """
    Create an administrator account (privileged channel only).

    ``channel`` must be one of: admin_api, admin_bootstrap, admin_cli, test_fixture.
    """
    from core.provisioning_context import AUTHORIZED_PRIVILEGED_CHANNELS

    validate_password(password)
    admin_role = "clinic_admin"
    if admin_role not in PRIVILEGED_ROLES:
        raise UserProvisioningError("Admin role is not configured.")
    if channel not in AUTHORIZED_PRIVILEGED_CHANNELS:
        raise PrivilegedRoleAssignmentError(
            f"Cannot create admin via unauthorized channel '{channel}'."
        )

    try:
        user = _persist_user(
            db,
            email=email,
            password=password,
            role=admin_role,
            channel=channel,
        )
    except IntegrityError as exc:
        db.rollback()
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            raise EmailAlreadyRegisteredError("Email already registered") from exc
        raise UserProvisioningError("Error creating administrator.") from exc

    if clinic_id is not None:
        user.clinic_id = clinic_id
        db.add(
            models.ClinicStaff(clinic_id=clinic_id, user_id=user.id, is_active=True)
        )
        db.commit()
        db.refresh(user)

    logger.info(
        "Administrator provisioned id=%s email=%s channel=%s actor_user_id=%s",
        user.id,
        user.email,
        channel,
        actor_user_id,
    )
    return ProvisionedUser(user=user, doctor_id=None)


def create_staff_user(
    db: Session,
    *,
    email: str,
    password: str,
    role: str,
    clinic_id: int,
    channel: str = "admin_api",
    actor_user_id: int | None = None,
) -> ProvisionedUser:
    """Create clinic staff (receptionist, cashier, lab_technician, pharmacist, doctor, admin)."""
    from core.roles import CLINICAL_STAFF_ROLES

    normalized = assert_known_role(role)
    if normalized not in CLINICAL_STAFF_ROLES | CLINIC_ADMIN_ROLES | {"platform_admin"}:
        raise UserProvisioningError(f"Role '{role}' is not a staff role.")
    if normalized in {"platform_owner", "platform_admin"}:
        raise PrivilegedRoleAssignmentError(
            "Platform roles cannot be assigned via staff provisioning."
        )

    try:
        validate_password(password)
    except ValueError as exc:
        raise UserProvisioningError(str(exc)) from exc

    try:
        user = _persist_user(
            db,
            email=email,
            password=password,
            role=normalized,
            channel=channel,
        )
    except IntegrityError as exc:
        db.rollback()
        err = str(exc).lower()
        if "ck_users_role_allowed" in err or "check constraint" in err:
            raise UserProvisioningError(
                f"Role '{role}' is not allowed by the database schema. Run migrations on the server."
            ) from exc
        if "email" in err or "unique" in err:
            raise EmailAlreadyRegisteredError("Email already registered") from exc
        raise UserProvisioningError("Error creating staff user.") from exc

    user.clinic_id = clinic_id
    db.add(
        models.ClinicStaff(clinic_id=clinic_id, user_id=user.id, is_active=True)
    )
    if normalized == "doctor":
        doc = _ensure_doctor_profile(db, user)
        doc.clinic_id = clinic_id
    db.commit()
    db.refresh(user)

    doctor_id = None
    if user.role == "doctor":
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if doc:
            doctor_id = doc.id

    logger.info(
        "Staff provisioned id=%s role=%s clinic_id=%s actor=%s",
        user.id,
        user.role,
        clinic_id,
        actor_user_id,
    )
    return ProvisionedUser(user=user, doctor_id=doctor_id)


def create_clinic_admin_user(
    db: Session,
    *,
    email: str,
    password: str,
    clinic_id: int,
    channel: str = "admin_api",
    actor_user_id: int | None = None,
) -> ProvisionedUser:
    """Platform owner provisions a clinic administrator."""
    validate_password(password)
    try:
        user = _persist_user(
            db,
            email=email,
            password=password,
            role="clinic_admin",
            channel=channel,
        )
    except IntegrityError as exc:
        db.rollback()
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            raise EmailAlreadyRegisteredError("Email already registered") from exc
        raise UserProvisioningError("Error creating clinic administrator.") from exc

    user.clinic_id = clinic_id
    db.add(models.ClinicStaff(clinic_id=clinic_id, user_id=user.id, is_active=True))
    db.commit()
    db.refresh(user)
    logger.info(
        "Clinic admin provisioned id=%s clinic_id=%s actor=%s",
        user.id,
        clinic_id,
        actor_user_id,
    )
    return ProvisionedUser(user=user, doctor_id=None)


def create_platform_owner_user(
    db: Session,
    *,
    email: str,
    password: str,
    channel: str = "platform_owner_bootstrap",
) -> ProvisionedUser:
    """Create the platform owner — bootstrap channel only."""
    validate_password(password)
    if db.query(User).filter(User.role == "platform_owner").first():
        raise UserProvisioningError("Platform owner already exists.")
    try:
        user = _persist_user(
            db,
            email=email,
            password=password,
            role="platform_owner",
            channel=channel,
        )
    except IntegrityError as exc:
        db.rollback()
        if "email" in str(exc).lower() or "unique" in str(exc).lower():
            raise EmailAlreadyRegisteredError("Email already registered") from exc
        raise UserProvisioningError("Error creating platform owner.") from exc
    logger.info("Platform owner provisioned id=%s email=%s", user.id, user.email)
    return ProvisionedUser(user=user, doctor_id=None)


def platform_owner_exists(db: Session) -> bool:
    return db.query(User).filter(User.role == "platform_owner").first() is not None


def setup_first_platform_owner(
    db: Session,
    *,
    email: str,
    password: str,
) -> ProvisionedUser:
    """Create the first platform owner via the public setup page (one-time)."""
    if platform_owner_exists(db):
        raise PlatformOwnerSetupClosedError(
            "Platform owner setup is disabled. Sign in with your owner account."
        )
    return create_platform_owner_user(
        db,
        email=email,
        password=password,
        channel="platform_owner_setup",
    )


def bootstrap_platform_owner(db: Session) -> User | None:
    """One-time Platform Owner bootstrap from env vars (production only)."""
    if os.getenv("ENABLE_PLATFORM_OWNER_BOOTSTRAP", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return None

    email = (os.getenv("PLATFORM_OWNER_EMAIL") or "").strip().lower()
    password = os.getenv("PLATFORM_OWNER_PASSWORD") or ""
    if not email or not password:
        logger.warning(
            "ENABLE_PLATFORM_OWNER_BOOTSTRAP set but PLATFORM_OWNER_EMAIL/PASSWORD missing."
        )
        return None

    if db.query(User).filter(User.role == "platform_owner").first():
        logger.info("Platform owner bootstrap skipped: owner already exists.")
        return None

    if _email_taken(db, email):
        user = db.query(User).filter(func.lower(User.email) == email).first()
        if user and user.role != "platform_owner":
            logger.error(
                "Platform owner bootstrap blocked: %s exists with role=%s",
                email,
                user.role,
            )
        return None

    try:
        provisioned = create_platform_owner_user(
            db,
            email=email,
            password=password,
            channel="platform_owner_bootstrap",
        )
    except UserProvisioningError as exc:
        logger.error("Platform owner bootstrap failed: %s", exc)
        return None

    logger.info("Bootstrapped platform owner: %s", provisioned.user.email)
    return provisioned.user


def bootstrap_initial_admin(db: Session) -> User | None:
    """
    One-time bootstrap when no admin exists (ops / first deploy).
    Controlled by ENABLE_ADMIN_BOOTSTRAP + ADMIN_BOOTSTRAP_EMAIL + ADMIN_BOOTSTRAP_PASSWORD.
    """
    if os.getenv("ENABLE_ADMIN_BOOTSTRAP", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return None

    email = (os.getenv("ADMIN_BOOTSTRAP_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD") or ""
    if not email or not password:
        logger.warning(
            "ENABLE_ADMIN_BOOTSTRAP is set but ADMIN_BOOTSTRAP_EMAIL/PASSWORD are missing; skipping."
        )
        return None

    existing_admin = db.query(User).filter(User.role == "admin").first()
    if existing_admin:
        logger.info("Admin bootstrap skipped: at least one admin already exists (id=%s).", existing_admin.id)
        return None

    if _email_taken(db, email):
        user = db.query(User).filter(func.lower(User.email) == email).first()
        if user and user.role != "admin":
            logger.error(
                "Admin bootstrap blocked: %s exists with role=%s (will not escalate via bootstrap).",
                email,
                user.role,
            )
        return None

    try:
        validate_password(password)
    except ValueError as exc:
        logger.error("Admin bootstrap password invalid: %s", exc)
        return None

    provisioned = create_admin_user(
        db,
        email=email,
        password=password,
        channel="admin_bootstrap",
    )
    logger.info("Bootstrapped initial admin: %s (id=%s)", provisioned.user.email, provisioned.user.id)
    return provisioned.user


def provision_cli_user(db: Session, *, email: str, password: str, role: str) -> ProvisionedUser:
    """
    CLI / dev script path. Admin only when ALLOW_ADMIN_CLI=true.
    """
    normalized = assert_known_role(role)
    if is_privileged_role(normalized):
        if os.getenv("ALLOW_ADMIN_CLI", "").strip().lower() not in {"1", "true", "yes", "on"}:
            raise PrivilegedRoleAssignmentError(
                "Admin accounts cannot be created via CLI. "
                "Set ALLOW_ADMIN_CLI=true for local ops, or use POST /users/admins."
            )
        return create_admin_user(
            db,
            email=email,
            password=password,
            channel="admin_cli",
        )

    return register_public_user(db, email=email, password=password, role=normalized)
