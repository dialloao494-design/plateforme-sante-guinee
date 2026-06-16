#!/usr/bin/env python3
"""
Idempotent staging seed for Railway/Vercel E2E multi-tenant testing.

Run on Railway after deploy:
  railway run python scripts/deploy/staging_e2e_seed.py

Or set ENABLE_STAGING_E2E_SEED=true in backend env (runs at container start).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func

import models
from core.provisioning_context import provisioning_channel
from database import SessionLocal
from security import hash_password, verify_password
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    create_admin_user,
    create_staff_user,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("staging_e2e_seed")

# Documented credentials for E2E testers (staging only).
ACCOUNTS = {
    "platform_admin": {
        "email": "platform.admin@sante-gn.test",
        "password": "PlatformAdmin1!",
        "role": "platform_admin",
    },
    "clinic_admin_a": {
        "email": "clinic.admin.a@sante-gn.test",
        "password": "ClinicAdminA1!",
        "role": "clinic_admin",
        "clinic_name": "Clinique Alpha Conakry",
    },
    "clinic_admin_b": {
        "email": "clinic.admin.b@sante-gn.test",
        "password": "ClinicAdminB1!",
        "role": "clinic_admin",
        "clinic_name": "Clinique Beta Conakry",
    },
    "doctor": {
        "email": "doctor.demo@sante-gn.test",
        "password": "DoctorDemo1!",
        "role": "doctor",
        "clinic_name": "Clinique Alpha Conakry",
    },
    "receptionist": {
        "email": "reception.demo@sante-gn.test",
        "password": "ReceptionDemo1!",
        "role": "receptionist",
        "clinic_name": "Clinique Alpha Conakry",
    },
    "receptionist_b": {
        "email": "reception.beta@sante-gn.test",
        "password": "ReceptionBeta1!",
        "role": "receptionist",
        "clinic_name": "Clinique Beta Conakry",
    },
}


def _get_or_create_clinic(db, name: str) -> models.Clinic:
    clinic = db.query(models.Clinic).filter(models.Clinic.name == name).first()
    if clinic:
        return clinic
    clinic = models.Clinic(name=name, city="Conakry", is_active=True)
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    logger.info("Created clinic id=%s name=%s", clinic.id, clinic.name)
    return clinic


def _sync_password(db, user: models.User, password: str) -> None:
    if not verify_password(password, user.hashed_password):
        user.hashed_password = hash_password(password)
        db.add(user)
        db.commit()


def _ensure_platform_admin(db) -> models.User:
    spec = ACCOUNTS["platform_admin"]
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == spec["email"].lower())
        .first()
    )
    if user:
        if user.role != "platform_admin":
            user.role = "platform_admin"
            db.commit()
        _sync_password(db, user, spec["password"])
        logger.info("Platform admin exists: %s", user.email)
        return user
    with provisioning_channel("admin_bootstrap"):
        created = create_admin_user(
            db,
            email=spec["email"],
            password=spec["password"],
            channel="admin_bootstrap",
        )
    logger.info("Created platform admin: %s", created.user.email)
    return created.user


def _ensure_clinic_staff(db, key: str, clinics: dict[str, models.Clinic]) -> models.User:
    spec = ACCOUNTS[key]
    clinic = clinics[spec["clinic_name"]]
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == spec["email"].lower())
        .first()
    )
    if user:
        if user.role != spec["role"]:
            user.role = spec["role"]
        user.clinic_id = clinic.id
        staff = (
            db.query(models.ClinicStaff)
            .filter(
                models.ClinicStaff.user_id == user.id,
                models.ClinicStaff.clinic_id == clinic.id,
            )
            .first()
        )
        if not staff:
            db.add(models.ClinicStaff(clinic_id=clinic.id, user_id=user.id, is_active=True))
        if spec["role"] == "doctor":
            doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
            if doc and doc.clinic_id != clinic.id:
                doc.clinic_id = clinic.id
        db.commit()
        _sync_password(db, user, spec["password"])
        logger.info("Staff exists: %s role=%s clinic=%s", user.email, user.role, clinic.name)
        return user

    with provisioning_channel("admin_bootstrap"):
        try:
            created = create_staff_user(
                db,
                email=spec["email"],
                password=spec["password"],
                role=spec["role"],
                clinic_id=clinic.id,
                channel="admin_bootstrap",
            )
        except EmailAlreadyRegisteredError:
            db.rollback()
            user = (
                db.query(models.User)
                .filter(func.lower(models.User.email) == spec["email"].lower())
                .first()
            )
            if not user:
                raise
            _sync_password(db, user, spec["password"])
            return user
    logger.info("Created staff: %s role=%s clinic=%s", created.user.email, spec["role"], clinic.name)
    return created.user


def main() -> int:
    db = SessionLocal()
    try:
        clinics = {
            ACCOUNTS["clinic_admin_a"]["clinic_name"]: _get_or_create_clinic(
                db, ACCOUNTS["clinic_admin_a"]["clinic_name"]
            ),
            ACCOUNTS["clinic_admin_b"]["clinic_name"]: _get_or_create_clinic(
                db, ACCOUNTS["clinic_admin_b"]["clinic_name"]
            ),
        }

        _ensure_platform_admin(db)
        _ensure_clinic_staff(db, "clinic_admin_a", clinics)
        _ensure_clinic_staff(db, "clinic_admin_b", clinics)
        _ensure_clinic_staff(db, "doctor", clinics)
        _ensure_clinic_staff(db, "receptionist", clinics)
        _ensure_clinic_staff(db, "receptionist_b", clinics)

        print("=== Staging E2E accounts ready ===")
        for key, spec in ACCOUNTS.items():
            clinic_note = f" @ {spec['clinic_name']}" if "clinic_name" in spec else ""
            print(f"  {key}: {spec['email']} / {spec['password']}{clinic_note}")
        return 0
    except Exception as exc:
        logger.exception("Staging seed failed: %s", exc)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
