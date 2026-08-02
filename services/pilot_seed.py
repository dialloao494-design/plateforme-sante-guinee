"""
Pilot / demo accounts — single source of truth for idempotent seeding.

Rules:
- Same emails and passwords on every run (no random password changes).
- Idempotent: safe to call on every API startup.
- No duplicate users: lookup by lower(email); create-or-sync only.
- Doctor profiles always aligned with pilot doctor users.

Passwords (must satisfy PASSWORD_MIN_LENGTH ≥ 12):
- All pilot doctors: DoctorPilot123!
- Pilot patient: PatientPilot123!
"""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from security import hash_password, verify_password
from services.user_provisioning import EmailAlreadyRegisteredError, register_public_user
from services.availability_service import AvailabilityService

logger = logging.getLogger(__name__)

PILOT_DOCTOR_PASSWORD = "DoctorPilot123!"
PILOT_PATIENT_PASSWORD = "PatientPilot123!"

# Canonical pilot doctor emails (stable for documentation & UX).
PILOT_DOCTORS: list[dict[str, Any]] = [
    {
        "email": "dr.amu@example.com",
        "first_name": "Amina",
        "last_name": "Barry",
        "specialty": "Pédiatrie",
        "location": "Conakry · Kaloum — Clinique médico-chirurgicale (CMS) Dixinn",
        "phone": "+224 620 00 00 01",
        "photo_url": "https://api.dicebear.com/7.x/female/svg?seed=AminaBarry",
        "consultation_fee": 45000.0,
        "latitude": 9.5092,
        "longitude": -13.7122,
    },
    {
        "email": "dr.souleimane@example.com",
        "first_name": "Souleymane",
        "last_name": "Diallo",
        "specialty": "Médecine générale",
        "location": "Conakry · Ratoma — Cabinet télésanté & suivi chronique",
        "phone": "+224 620 00 00 02",
        "photo_url": "https://api.dicebear.com/7.x/male/svg?seed=SouleymaneDiallo",
        "consultation_fee": 40000.0,
        "latitude": 9.5766,
        "longitude": -13.6478,
    },
    {
        "email": "dr.fatou@example.com",
        "first_name": "Fatoumata",
        "last_name": "Kaba",
        "specialty": "Dermatologie",
        "location": "Kindia — Centre de santé urbain, consultations hybrides",
        "phone": "+224 620 00 00 03",
        "photo_url": "https://api.dicebear.com/7.x/female/svg?seed=FatoumataKaba",
        "consultation_fee": 42000.0,
        "latitude": 10.0569,
        "longitude": -12.8658,
    },
    {
        "email": "dr.mamady@example.com",
        "first_name": "Mamady",
        "last_name": "Keïta",
        "specialty": "Cardiologie",
        "location": "Conakry · Matam — Consultations HTA & suivi cardiaque",
        "phone": "+224 620 00 00 04",
        "photo_url": "https://api.dicebear.com/7.x/male/svg?seed=MamadyKeita",
        "consultation_fee": 55000.0,
        "latitude": 9.5629,
        "longitude": -13.6014,
    },
]

PILOT_PATIENT_EMAIL = "test.patient@example.com"

# Demo-friendly working hours — synced on every pilot seed (Mon–Sun, wide window).
PILOT_DEMO_AVAILABILITY_START = time(8, 0)
PILOT_DEMO_AVAILABILITY_END = time(20, 0)
PILOT_DEMO_AVAILABILITY_DAYS = range(7)

# Legacy typo from earlier seeds — merge into canonical email if present.
_LEGACY_DOCTOR_EMAIL_RENAMES = {
    "dr.soulaiman@example.com": "dr.souleimane@example.com",
}


def _rename_legacy_emails(db: Session) -> None:
    for old_email, new_email in _LEGACY_DOCTOR_EMAIL_RENAMES.items():
        old_l = old_email.lower().strip()
        new_l = new_email.lower().strip()
        old_user = db.query(models.User).filter(func.lower(models.User.email) == old_l).first()
        new_user = db.query(models.User).filter(func.lower(models.User.email) == new_l).first()
        if old_user and not new_user:
            old_user.email = new_l
            db.commit()
            logger.info("Renamed legacy pilot email %s → %s", old_l, new_l)


def _ensure_user_doctor(db: Session, email: str, plain_password: str, profile: dict[str, Any]) -> None:
    email = email.lower().strip()
    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    if not user:
        try:
            provisioned = register_public_user(
                db,
                email=email,
                password=plain_password,
                role="doctor",
            )
            user = provisioned.user
        except EmailAlreadyRegisteredError:
            user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
        logger.info("Pilot seed: created doctor user %s", email)
    else:
        changed = False
        if (user.email or "").lower() != email:
            user.email = email
            changed = True
        try:
            pwd_ok = verify_password(plain_password, user.hashed_password)
        except Exception:
            pwd_ok = False
        if not pwd_ok:
            user.hashed_password = hash_password(plain_password)
            changed = True
            logger.info("Pilot seed: repaired password hash for %s (was not DoctorPilot123!)", email)
        if user.role != "doctor":
            user.role = "doctor"
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
    if not doc:
        doc = models.Doctor(
            user_id=user.id,
            first_name=profile["first_name"],
            last_name=profile["last_name"],
            specialty=profile["specialty"],
            city=profile["location"],
            phone=profile["phone"],
            photo_url=profile.get("photo_url"),
            consultation_fee=float(profile.get("consultation_fee", 0)),
            latitude=profile.get("latitude"),
            longitude=profile.get("longitude"),
        )
        db.add(doc)
        db.commit()
        logger.info("Pilot seed: created doctor profile for %s", email)
        return

    sync_fields = (
        ("first_name", profile["first_name"]),
        ("last_name", profile["last_name"]),
        ("specialty", profile["specialty"]),
        ("city", profile["location"]),
        ("phone", profile["phone"]),
        ("photo_url", profile.get("photo_url")),
        ("consultation_fee", float(profile.get("consultation_fee", 0))),
        ("latitude", profile.get("latitude")),
        ("longitude", profile.get("longitude")),
    )
    changed = False
    for attr, value in sync_fields:
        if value is None and attr in ("latitude", "longitude", "photo_url"):
            continue
        if getattr(doc, attr, None) != value:
            setattr(doc, attr, value)
            changed = True
    if changed:
        db.commit()
        logger.info("Pilot seed: synced doctor profile for %s", email)


def _ensure_pilot_patient(db: Session) -> None:
    email = PILOT_PATIENT_EMAIL.lower().strip()
    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    if not user:
        try:
            provisioned = register_public_user(
                db,
                email=email,
                password=PILOT_PATIENT_PASSWORD,
                role="patient",
            )
            user = provisioned.user
        except EmailAlreadyRegisteredError:
            user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
        logger.info("Pilot seed: created patient user %s", email)
    else:
        changed = False
        try:
            pwd_ok = verify_password(PILOT_PATIENT_PASSWORD, user.hashed_password)
        except Exception:
            pwd_ok = False
        if not pwd_ok:
            user.hashed_password = hash_password(PILOT_PATIENT_PASSWORD)
            changed = True
            logger.info("Pilot seed: repaired password hash for %s (was not PatientPilot123!)", email)
        if user.role != "patient":
            user.role = "patient"
            changed = True
        if changed:
            db.commit()
            db.refresh(user)

    prof = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
    if not prof:
        prof = models.Patient(
            user_id=user.id,
            first_name="Test",
            last_name="Patient",
            age=30,
            gender="other",
        )
        db.add(prof)
        db.commit()
        logger.info("Pilot seed: created patient profile for %s", email)
    else:
        # Light sync — do not overwrite real pilot edits to names if you prefer; keep stable demo names.
        if (prof.first_name or "") != "Test" or (prof.last_name or "") != "Patient":
            prof.first_name = "Test"
            prof.last_name = "Patient"
            db.commit()


def _ensure_pilot_availability(db: Session) -> None:
    """Ensure all pilot doctors accept bookings 08:00–20:00 every day (demo)."""
    for row in PILOT_DOCTORS:
        email = row["email"].lower().strip()
        user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
        if not user:
            continue
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if not doc:
            continue
        for day in PILOT_DEMO_AVAILABILITY_DAYS:
            AvailabilityService.set_doctor_working_hours(
                doctor_id=doc.id,
                day_of_week=day,
                start_time=PILOT_DEMO_AVAILABILITY_START,
                end_time=PILOT_DEMO_AVAILABILITY_END,
                db=db,
            )
        logger.info(
            "Pilot seed: demo availability %s–%s (7j) for %s",
            PILOT_DEMO_AVAILABILITY_START.strftime("%H:%M"),
            PILOT_DEMO_AVAILABILITY_END.strftime("%H:%M"),
            email,
        )


def seed_pilot_accounts() -> None:
    """
    Idempotent pilot seed. Call once per process startup (or from reset script).
    Uses its own SessionLocal scope.
    """
    from database import SessionLocal

    db = SessionLocal()
    try:
        _rename_legacy_emails(db)
        for row in PILOT_DOCTORS:
            _ensure_user_doctor(db, row["email"], PILOT_DOCTOR_PASSWORD, row)
        _ensure_pilot_patient(db)
        _ensure_pilot_availability(db)
        logger.info("Pilot seed: all accounts verified.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
