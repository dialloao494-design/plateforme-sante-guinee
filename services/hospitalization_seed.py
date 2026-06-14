"""Seed default hospital rooms and beds for pilot clinic."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

import models

logger = logging.getLogger(__name__)

DEFAULT_ROOMS = [
    ("Médecine", "101", "general", 2, ["A", "B"]),
    ("Médecine", "102", "general", 2, ["A", "B"]),
    ("Chirurgie", "201", "general", 2, ["1", "2"]),
    ("Maternité", "301", "maternity", 1, ["1"]),
]


def seed_hospitalization(db: Session, clinic_id: int) -> None:
    existing = db.query(models.HospitalRoom).filter(models.HospitalRoom.clinic_id == clinic_id).count()
    if existing:
        logger.info("Hospitalization seed skipped — rooms already exist for clinic %s", clinic_id)
        return
    for ward, room_num, room_type, capacity, bed_nums in DEFAULT_ROOMS:
        room = models.HospitalRoom(
            clinic_id=clinic_id,
            ward_name=ward,
            room_number=room_num,
            room_type=room_type,
            capacity=capacity,
        )
        db.add(room)
        db.flush()
        for bn in bed_nums:
            db.add(models.HospitalBed(room_id=room.id, bed_number=bn))
    db.commit()
    logger.info("Seeded %s hospital rooms for clinic %s", len(DEFAULT_ROOMS), clinic_id)
