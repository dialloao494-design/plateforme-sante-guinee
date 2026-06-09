#!/usr/bin/env python3
"""Provision demo doctors + 5 availability slots each (one-shot, ENABLE_PILOT_SEED=false at boot)."""
from __future__ import annotations

import os
import sys

# Ensure project root on path when run via docker exec
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import time

from database import SessionLocal
import models
from models.availability import DoctorAvailability
from services.availability_service import AvailabilityService
from services.pilot_seed import PILOT_DOCTORS, seed_pilot_accounts


def main() -> int:
    print("=== PILOT PROVISION — demo accounts + availability ===")
    seed_pilot_accounts()

    db = SessionLocal()
    try:
        doctors = db.query(models.Doctor).all()
        print(f"Doctors in DB: {len(doctors)}")
        created = 0
        for doc in doctors:
            existing = (
                db.query(DoctorAvailability)
                .filter(DoctorAvailability.doctor_id == doc.id, DoctorAvailability.is_active.is_(True))
                .count()
            )
            if existing >= 5:
                print(f"  doctor_id={doc.id} already has {existing} slots — skip")
                continue
            # 5 weekdays Mon–Fri 09:00–12:00
            for day in range(5):
                AvailabilityService.set_doctor_working_hours(
                    doctor_id=doc.id,
                    day_of_week=day,
                    start_time=time(9, 0),
                    end_time=time(12, 0),
                    db=db,
                )
                created += 1
            db.commit()
            print(f"  doctor_id={doc.id} ({doc.first_name} {doc.last_name}) → +5 slots")
        total = db.query(DoctorAvailability).count()
        print(f"Availability slots total: {total} (created {created})")
        print(f"Pilot doctors seeded: {len(PILOT_DOCTORS)} canonical emails")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
