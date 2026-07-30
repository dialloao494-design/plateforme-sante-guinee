#!/usr/bin/env python3
"""
Reset transactional QA data while keeping pilot demo accounts.

Removes: appointments, messages, payments, notifications, doctor availability slots.
Keeps: pilot doctors + test.patient (re-synced via pilot_seed).
Removes: non-pilot users and their profiles.

Usage (repo root, API stopped or not — uses own DB session):
  python scripts/reset_qa_lab.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    os.chdir(ROOT)
    from dotenv import load_dotenv

    load_dotenv()

    from sqlalchemy import func
    from database import SessionLocal
    import models
    from services.pilot_seed import (
        PILOT_DOCTORS,
        PILOT_PATIENT_EMAIL,
        seed_pilot_accounts,
    )

    allow_emails = {d["email"].lower().strip() for d in PILOT_DOCTORS}
    allow_emails.add(PILOT_PATIENT_EMAIL.lower().strip())

    db = SessionLocal()
    try:
        msg_n = db.query(models.Message).delete(synchronize_session=False)
        pay_n = db.query(models.Payment).delete(synchronize_session=False)
        notif_n = db.query(models.NotificationEvent).delete(synchronize_session=False)
        appt_n = db.query(models.RendezVous).delete(synchronize_session=False)
        from models.availability import DoctorAvailability

        avail_n = db.query(DoctorAvailability).delete(synchronize_session=False)

        extra_users = (
            db.query(models.User)
            .filter(~func.lower(models.User.email).in_(list(allow_emails)))
            .all()
        )
        removed_users = 0
        for user in extra_users:
            db.query(models.NotificationEvent).filter(
                models.NotificationEvent.user_id == user.id
            ).delete(synchronize_session=False)
            doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
            if doc:
                db.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == doc.id).delete(
                    synchronize_session=False
                )
                db.delete(doc)
            pat = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
            if pat:
                db.delete(pat)
            db.delete(user)
            removed_users += 1

        db.commit()
        print(f"Deleted: {appt_n} appointments, {msg_n} messages, {pay_n} payments, {notif_n} notifications, {avail_n} availability slots.")
        print(f"Removed {removed_users} non-pilot user(s).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    seed_pilot_accounts()
    print("Pilot accounts re-synced (passwords [REDACTED] / [REDACTED]).")
    print("Schedules are empty — add availability from doctor profile or API before booking.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
