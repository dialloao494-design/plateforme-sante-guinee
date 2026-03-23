"""
Doctor Availability Service

Utilities for managing and validating doctor working hours and appointment availability.
"""

from datetime import datetime, time, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import models


class AvailabilityService:
    """Service for managing doctor availability and working hours."""

    # Day names for user-friendly messages
    DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    @staticmethod
    def get_day_name(day_of_week: int) -> str:
        """Get readable day name from day_of_week (0-6)."""
        if 0 <= day_of_week <= 6:
            return AvailabilityService.DAY_NAMES[day_of_week]
        return "Unknown"

    @staticmethod
    def validate_working_hours(start_time: time, end_time: time) -> None:
        """Validate that working hours are properly formatted."""
        if end_time <= start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_time must be after start_time"
            )

    @staticmethod
    def get_doctor_schedule(doctor_id: int, db: Session) -> dict:
        """
        Get doctor's complete weekly schedule.
        
        Returns:
            dict: {
              "Monday": {"start": "09:00", "end": "17:00"},
              "Tuesday": {"start": "09:00", "end": "17:00"},
              ...
            }
        """
        slots = (
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor_id,
                models.DoctorAvailability.is_active == True,
            )
            .order_by(models.DoctorAvailability.day_of_week)
            .all()
        )

        schedule = {}
        for slot in slots:
            day_name = AvailabilityService.get_day_name(slot.day_of_week)
            schedule[day_name] = {
                "start": slot.start_time.strftime("%H:%M"),
                "end": slot.end_time.strftime("%H:%M"),
                "id": slot.id,
                "is_active": slot.is_active
            }

        return schedule

    @staticmethod
    def is_appointment_within_working_hours(
        doctor_id: int,
        appointment_start: datetime,
        duration_minutes: int,
        db: Session
    ) -> tuple[bool, str]:
        """
        Check if appointment falls within doctor's working hours.
        
        Args:
            doctor_id: Doctor ID
            appointment_start: Appointment start datetime
            duration_minutes: Appointment duration
            db: Database session
            
        Returns:
            tuple: (is_available: bool, message: str)
        """
        appointment_end = appointment_start + timedelta(minutes=duration_minutes)
        appointment_day = appointment_start.weekday()  # 0 = Monday, 6 = Sunday
        appointment_start_time = appointment_start.time()
        appointment_end_time = appointment_end.time()

        # Get availability for this day
        availability_slot = (
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor_id,
                models.DoctorAvailability.day_of_week == appointment_day,
                models.DoctorAvailability.is_active == True,
            )
            .first()
        )

        if not availability_slot:
            day_name = AvailabilityService.get_day_name(appointment_day)
            return False, f"Doctor has no working hours scheduled for {day_name}"

        # Check if times fall within working hours
        if (availability_slot.start_time <= appointment_start_time and 
            appointment_end_time <= availability_slot.end_time):
            return True, ""

        # Outside working hours
        return False, (
            f"Appointment {appointment_start_time.strftime('%H:%M')}-"
            f"{appointment_end_time.strftime('%H:%M')} "
            f"outside working hours {availability_slot.start_time.strftime('%H:%M')}-"
            f"{availability_slot.end_time.strftime('%H:%M')}"
        )

    @staticmethod
    def set_doctor_working_hours(
        doctor_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time,
        db: Session
    ) -> models.DoctorAvailability:
        """
        Set or update doctor's working hours for a specific day.
        
        Args:
            doctor_id: Doctor ID
            day_of_week: 0=Monday ... 6=Sunday
            start_time: Working hours start
            end_time: Working hours end
            db: Database session
            
        Returns:
            DoctorAvailability instance
            
        Raises:
            HTTPException if validation fails
        """
        # Validate day of week
        if not 0 <= day_of_week <= 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="day_of_week must be between 0 (Monday) and 6 (Sunday)"
            )

        AvailabilityService.validate_working_hours(start_time, end_time)

        # Check if slot already exists for this day
        existing_slot = (
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor_id,
                models.DoctorAvailability.day_of_week == day_of_week,
                models.DoctorAvailability.is_active == True,
            )
            .first()
        )

        if existing_slot:
            # Update existing slot
            existing_slot.start_time = start_time
            existing_slot.end_time = end_time
            db.commit()
            db.refresh(existing_slot)
            return existing_slot

        # Create new slot
        new_slot = models.DoctorAvailability(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        db.add(new_slot)
        db.commit()
        db.refresh(new_slot)
        return new_slot

    @staticmethod
    def disable_working_day(doctor_id: int, day_of_week: int, db: Session) -> None:
        """Disable all availability slots for a specific day."""
        slots = (
            db.query(models.DoctorAvailability)
            .filter(
                models.DoctorAvailability.doctor_id == doctor_id,
                models.DoctorAvailability.day_of_week == day_of_week,
            )
            .all()
        )

        for slot in slots:
            slot.is_active = False

        db.commit()
