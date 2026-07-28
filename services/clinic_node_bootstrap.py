"""Clinic Node bootstrap — local clinic + clinic_admin (idempotent, offline-safe)."""

from __future__ import annotations

import logging
import os
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    UserProvisioningError,
    create_clinic_admin_user,
    create_staff_user,
)

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_clinic_node() -> bool:
    return (os.getenv("ENVIRONMENT") or "").strip().lower() in {"clinic-node", "clinic_node"}


def bootstrap_clinic_node(db: Session) -> dict | None:
    """
    Create the local clinic and clinic_admin if missing.

    Controlled by ENABLE_CLINIC_NODE_BOOTSTRAP=true (clinic-node only).
    Never changes an existing user's password or role.
    """
    if not _is_clinic_node():
        return None
    if not _env_flag("ENABLE_CLINIC_NODE_BOOTSTRAP", default=False):
        logger.info("Clinic Node bootstrap skipped (ENABLE_CLINIC_NODE_BOOTSTRAP not set).")
        return None

    clinic_name = (os.getenv("CLINIC_NODE_CLINIC_NAME") or "Clinique Locale").strip()
    clinic_city = (os.getenv("CLINIC_NODE_CLINIC_CITY") or "").strip() or None
    admin_email = (os.getenv("CLINIC_NODE_ADMIN_EMAIL") or "").strip().lower()
    admin_password = os.getenv("CLINIC_NODE_ADMIN_PASSWORD") or ""

    if not admin_email or not admin_password:
        logger.error(
            "Clinic Node bootstrap enabled but CLINIC_NODE_ADMIN_EMAIL/PASSWORD missing; skipping."
        )
        return None

    result: dict = {"clinic_id": None, "admin_user_id": None, "created_clinic": False, "created_admin": False}

    clinic = None
    clinic_id_env = (os.getenv("CLINIC_ID") or "").strip()
    if clinic_id_env.isdigit():
        clinic = db.query(models.Clinic).filter(models.Clinic.id == int(clinic_id_env)).first()

    if clinic is None:
        clinic = (
            db.query(models.Clinic)
            .filter(func.lower(models.Clinic.name) == clinic_name.lower())
            .order_by(models.Clinic.id.asc())
            .first()
        )

    if clinic is None:
        clinic = models.Clinic(
            name=clinic_name,
            city=clinic_city,
            is_active=True,
        )
        db.add(clinic)
        db.commit()
        db.refresh(clinic)
        result["created_clinic"] = True
        logger.info("Clinic Node bootstrap: created clinic id=%s name=%s", clinic.id, clinic.name)
    else:
        logger.info("Clinic Node bootstrap: reusing clinic id=%s", clinic.id)

    result["clinic_id"] = clinic.id

    existing_admin = (
        db.query(models.User)
        .filter(
            models.User.clinic_id == clinic.id,
            models.User.role.in_(("clinic_admin", "admin")),
            models.User.is_active.is_(True),
        )
        .order_by(models.User.id.asc())
        .first()
    )
    if existing_admin:
        result["admin_user_id"] = existing_admin.id
        logger.info(
            "Clinic Node bootstrap: clinic_admin already exists id=%s email=%s",
            existing_admin.id,
            existing_admin.email,
        )
    else:
        email_user = (
            db.query(models.User).filter(func.lower(models.User.email) == admin_email).first()
        )
        if email_user:
            # Attach existing matching email if it is already a clinic admin without clinic.
            if email_user.role in ("clinic_admin", "admin") and not email_user.clinic_id:
                email_user.clinic_id = clinic.id
                staff = (
                    db.query(models.ClinicStaff)
                    .filter(
                        models.ClinicStaff.clinic_id == clinic.id,
                        models.ClinicStaff.user_id == email_user.id,
                    )
                    .first()
                )
                if not staff:
                    db.add(
                        models.ClinicStaff(
                            clinic_id=clinic.id, user_id=email_user.id, is_active=True
                        )
                    )
                db.commit()
                result["admin_user_id"] = email_user.id
                logger.info(
                    "Clinic Node bootstrap: attached existing admin id=%s to clinic %s",
                    email_user.id,
                    clinic.id,
                )
            else:
                logger.error(
                    "Clinic Node bootstrap blocked: %s exists with role=%s clinic_id=%s",
                    admin_email,
                    email_user.role,
                    email_user.clinic_id,
                )
                return result
        else:
            try:
                provisioned = create_clinic_admin_user(
                    db,
                    email=admin_email,
                    password=admin_password,
                    clinic_id=clinic.id,
                    channel="clinic_node_bootstrap",
                )
            except (EmailAlreadyRegisteredError, UserProvisioningError, ValueError) as exc:
                logger.error("Clinic Node admin bootstrap failed: %s", exc)
                return result
            # Force password change on first login for installer-chosen shared passwords.
            if _env_flag("CLINIC_NODE_ADMIN_MUST_CHANGE_PASSWORD", default=True):
                provisioned.user.must_change_password = True
                db.commit()
            result["admin_user_id"] = provisioned.user.id
            result["created_admin"] = True
            logger.info(
                "Clinic Node bootstrap: created clinic_admin id=%s email=%s",
                provisioned.user.id,
                admin_email,
            )

    if _env_flag("CLINIC_NODE_BOOTSTRAP_STAFF", default=False):
        _bootstrap_optional_staff(db, clinic.id)

    # Persist clinic id hint for ops (node metadata file is optional later).
    os.environ.setdefault("CLINIC_ID", str(clinic.id))
    return result


def _bootstrap_optional_staff(db: Session, clinic_id: int) -> None:
    """Optional role accounts for LAN multi-user smoke tests (not production defaults)."""
    suffix = (os.getenv("CLINIC_NODE_STAFF_EMAIL_DOMAIN") or "clinic.local").strip().lower()
    password = os.getenv("CLINIC_NODE_STAFF_PASSWORD") or ""
    if not password:
        # Derive a unique strong password if unset — logged once at INFO for installer evidence.
        password = f"ChangeMe-{uuid.uuid4().hex[:12]}!"
        logger.warning(
            "CLINIC_NODE_STAFF_PASSWORD unset; generated temporary staff password for this boot only."
        )

    roles = (
        ("receptionist", f"reception@{suffix}"),
        ("doctor", f"doctor@{suffix}"),
        ("nurse", f"nurse@{suffix}"),
        ("lab_technician", f"lab@{suffix}"),
        ("pharmacist", f"pharmacy@{suffix}"),
        ("cashier", f"cashier@{suffix}"),
    )
    for role, email in roles:
        existing = db.query(models.User).filter(func.lower(models.User.email) == email).first()
        if existing:
            continue
        try:
            create_staff_user(
                db,
                email=email,
                password=password,
                role=role,
                clinic_id=clinic_id,
                channel="clinic_node_bootstrap",
            )
            user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
            if user:
                user.must_change_password = True
                db.commit()
            logger.info("Clinic Node bootstrap staff: created %s (%s)", email, role)
        except Exception as exc:
            logger.error("Clinic Node bootstrap staff failed for %s: %s", email, exc)
