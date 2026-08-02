"""
Idempotent CIS pilot clinic + staff seed.

Ensures:
- A default pilot clinic exists (Clinique Pilote CIS).
- Role accounts @pilot.local exist with clinic_id and known passwords.
- All demo doctor profiles (pilot_seed) are linked to the pilot clinic.

Without clinic_id on staff/doctors, clinical APIs return:
  "User is not assigned to a clinic"
"""

from __future__ import annotations

import logging

from sqlalchemy import func

import models
from security import hash_password, verify_password
from services.pilot_seed import PILOT_DOCTORS
from services.user_provisioning import EmailAlreadyRegisteredError, create_staff_user

logger = logging.getLogger(__name__)

PILOT_CLINIC_NAME = "Clinique Pilote CIS"
PILOT_CLINIC_CITY = "Conakry"

# Canonical CIS demo staff — same credentials documented for clinic readiness tests.
PILOT_STAFF: list[dict[str, str]] = [
    {"email": "admin@pilot.local", "password": "AdminPilot1!", "role": "admin"},
    {"email": "reception@pilot.local", "password": "ReceptionPilot1!", "role": "receptionist"},
    {"email": "cashier@pilot.local", "password": "CashierPilot1!", "role": "cashier"},
    {"email": "dr.pilot@pilot.local", "password": "DoctorPilot1!", "role": "doctor"},
    {"email": "lab@pilot.local", "password": "LabPilot123!", "role": "lab_technician"},
    {"email": "pharmacy@pilot.local", "password": "PharmacyPilot1!", "role": "pharmacist"},
]


def _ensure_pilot_clinic(db) -> models.Clinic:
    clinic = (
        db.query(models.Clinic)
        .filter(func.lower(models.Clinic.name) == PILOT_CLINIC_NAME.lower())
        .order_by(models.Clinic.id.asc())
        .first()
    )
    if clinic:
        return clinic
    clinic = models.Clinic(name=PILOT_CLINIC_NAME, city=PILOT_CLINIC_CITY, is_active=True)
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    logger.info("CIS pilot seed: created clinic id=%s", clinic.id)
    return clinic


def _ensure_clinic_staff_row(db, clinic_id: int, user_id: int) -> None:
    row = (
        db.query(models.ClinicStaff)
        .filter(models.ClinicStaff.clinic_id == clinic_id, models.ClinicStaff.user_id == user_id)
        .first()
    )
    if not row:
        db.add(models.ClinicStaff(clinic_id=clinic_id, user_id=user_id, is_active=True))
        db.commit()


def _assign_user_to_clinic(db, user: models.User, clinic_id: int) -> None:
    if user.clinic_id != clinic_id:
        user.clinic_id = clinic_id
    _ensure_clinic_staff_row(db, clinic_id, user.id)
    if user.role == "doctor":
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if doc and doc.clinic_id != clinic_id:
            doc.clinic_id = clinic_id
    db.commit()


def _ensure_staff_account(db, clinic_id: int, email: str, password: str, role: str) -> None:
    email_l = email.lower().strip()
    user = db.query(models.User).filter(func.lower(models.User.email) == email_l).first()
    if not user:
        try:
            create_staff_user(
                db,
                email=email_l,
                password=password,
                role=role,
                clinic_id=clinic_id,
                channel="admin_api",
            )
            logger.info("CIS pilot seed: created staff %s (%s)", email_l, role)
            return
        except EmailAlreadyRegisteredError:
            user = db.query(models.User).filter(func.lower(models.User.email) == email_l).first()
    if not user:
        return
    changed = False
    if user.role != role:
        user.role = role
        changed = True
    try:
        pwd_ok = verify_password(password, user.hashed_password)
    except Exception:
        pwd_ok = False
    if not pwd_ok:
        user.hashed_password = hash_password(password)
        changed = True
        logger.info("CIS pilot seed: repaired password hash for %s", email_l)
    if changed:
        db.commit()
        db.refresh(user)
    _assign_user_to_clinic(db, user, clinic_id)
    logger.info("CIS pilot seed: synced staff %s clinic_id=%s", email_l, clinic_id)


def _link_demo_doctors_to_clinic(db, clinic_id: int) -> None:
    for row in PILOT_DOCTORS:
        email_l = row["email"].lower().strip()
        user = db.query(models.User).filter(func.lower(models.User.email) == email_l).first()
        if not user or user.role != "doctor":
            continue
        _assign_user_to_clinic(db, user, clinic_id)
        logger.info("CIS pilot seed: linked demo doctor %s to clinic %s", email_l, clinic_id)


def seed_clinic_pilot_accounts() -> None:
    from database import SessionLocal

    db = SessionLocal()
    try:
        clinic = _ensure_pilot_clinic(db)
        for spec in PILOT_STAFF:
            _ensure_staff_account(db, clinic.id, spec["email"], spec["password"], spec["role"])
        _link_demo_doctors_to_clinic(db, clinic.id)
        from services.hospitalization_seed import seed_hospitalization

        seed_hospitalization(db, clinic.id)
        logger.info("CIS pilot seed complete (clinic_id=%s).", clinic.id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
