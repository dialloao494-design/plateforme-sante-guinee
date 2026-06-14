#!/usr/bin/env python3
"""Provision demo doctors + wide availability slots (08:00–20:00, Mon–Sun)."""
from __future__ import annotations

import os
import sys

# Ensure project root on path when run via docker exec
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
from models.availability import DoctorAvailability
from services.pilot_seed import (
    PILOT_DEMO_AVAILABILITY_DAYS,
    PILOT_DEMO_AVAILABILITY_END,
    PILOT_DEMO_AVAILABILITY_START,
    PILOT_DOCTORS,
    seed_pilot_accounts,
    _ensure_pilot_availability,
)


def main() -> int:
    print("=== PILOT PROVISION — demo accounts + availability ===")
    seed_pilot_accounts()

    db = SessionLocal()
    try:
        doctors = db.query(models.Doctor).all()
        print(f"Doctors in DB: {len(doctors)}")
        _ensure_pilot_availability(db)
        total = db.query(DoctorAvailability).filter(DoctorAvailability.is_active.is_(True)).count()
        print(
            f"Availability synced: {PILOT_DEMO_AVAILABILITY_START.strftime('%H:%M')}-"
            f"{PILOT_DEMO_AVAILABILITY_END.strftime('%H:%M')} × {len(PILOT_DEMO_AVAILABILITY_DAYS)} days/doctor"
        )
        print(f"Active slots total: {total}")
        print(f"Pilot doctors: {len(PILOT_DOCTORS)} canonical emails")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
