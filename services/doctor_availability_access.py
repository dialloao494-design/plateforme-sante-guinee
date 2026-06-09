"""
Doctor availability mutations — ownership enforcement + orchestration.

All schedule writes (create / update / deactivate) MUST pass through this module
so IDOR on ``/doctors/{doctor_id}/availability`` cannot recur at the router layer.
"""

from __future__ import annotations

import logging
from datetime import time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.doctor_ownership_policy import DoctorOwnershipPolicy
from models.user import User
from schemas.availability import DoctorAvailabilityCreate, DoctorAvailabilityUpdate
from services.availability_service import AvailabilityService

logger = logging.getLogger(__name__)


class DoctorAvailabilityAccessService:
    @staticmethod
    def _assert_mutate_access(db: Session, doctor_id: int, current_user: User) -> None:
        DoctorOwnershipPolicy.assert_can_mutate_doctor_resource(
            db,
            target_doctor_id=doctor_id,
            current_user=current_user,
            resource="doctor availability schedule",
        )

    @staticmethod
    def create_slot(
        db: Session,
        *,
        doctor_id: int,
        payload: DoctorAvailabilityCreate,
        current_user: User,
    ) -> models.DoctorAvailability:
        DoctorAvailabilityAccessService._assert_mutate_access(db, doctor_id, current_user)

        if doctor_id != payload.doctor_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor ID mismatch")

        doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
        if not doctor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

        existing = (
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor_id,
                models.DoctorAvailability.day_of_week == payload.day_of_week,
                models.DoctorAvailability.is_active == True,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Doctor already has an availability slot for day {payload.day_of_week}",
            )

        new_slot = models.DoctorAvailability(
            doctor_id=doctor_id,
            day_of_week=payload.day_of_week,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        db.add(new_slot)
        db.commit()
        db.refresh(new_slot)

        logger.info(
            "Availability created doctor_id=%s slot_id=%s user_id=%s role=%s",
            doctor_id,
            new_slot.id,
            current_user.id,
            current_user.role,
        )
        return new_slot

    @staticmethod
    def update_slot(
        db: Session,
        *,
        doctor_id: int,
        availability_id: int,
        payload: DoctorAvailabilityUpdate,
        current_user: User,
    ) -> models.DoctorAvailability:
        DoctorAvailabilityAccessService._assert_mutate_access(db, doctor_id, current_user)

        slot = DoctorOwnershipPolicy.assert_availability_slot_belongs_to_doctor(
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor_id,
                models.DoctorAvailability.id == availability_id,
            )
            .first(),
            doctor_id=doctor_id,
        )

        if payload.day_of_week is not None:
            existing = (
                db.query(models.DoctorAvailability)
                .filter(
                    models.DoctorAvailability.doctor_id == doctor_id,
                    models.DoctorAvailability.day_of_week == payload.day_of_week,
                    models.DoctorAvailability.id != availability_id,
                    models.DoctorAvailability.is_active == True,
                )
                .first()
            )
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot already exists for this day")
            slot.day_of_week = payload.day_of_week

        if payload.start_time is not None:
            slot.start_time = payload.start_time
        if payload.end_time is not None:
            slot.end_time = payload.end_time
        if payload.is_active is not None:
            slot.is_active = payload.is_active

        if slot.end_time <= slot.start_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_time must be after start_time")

        db.commit()
        db.refresh(slot)

        logger.info(
            "Availability updated doctor_id=%s slot_id=%s user_id=%s role=%s",
            doctor_id,
            slot.id,
            current_user.id,
            current_user.role,
        )
        return slot

    @staticmethod
    def deactivate_slot(
        db: Session,
        *,
        doctor_id: int,
        availability_id: int,
        current_user: User,
    ) -> dict[str, str]:
        DoctorAvailabilityAccessService._assert_mutate_access(db, doctor_id, current_user)

        slot = DoctorOwnershipPolicy.assert_availability_slot_belongs_to_doctor(
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor_id,
                models.DoctorAvailability.id == availability_id,
            )
            .first(),
            doctor_id=doctor_id,
        )

        slot.is_active = False
        db.commit()

        logger.info(
            "Availability deactivated doctor_id=%s slot_id=%s user_id=%s role=%s",
            doctor_id,
            slot.id,
            current_user.id,
            current_user.role,
        )
        return {"detail": "Availability slot disabled"}
