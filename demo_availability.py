#!/usr/bin/env python3
"""
Demo script for Doctor Availability System

Shows how to:
1. Setup doctor working hours
2. Check appointment availability
3. Create appointments with availability validation
4. View doctor schedules
"""

from datetime import datetime, time, timedelta
from sqlalchemy.orm import Session
from services.availability_service import AvailabilityService
from services.rendezvous_service import RendezVousService
import models


def demo_setup_doctor_availability(db: Session):
    """Setup a doctor's weekly schedule."""
    print("\n=== Setting up Doctor's Weekly Schedule ===\n")

    doctor_id = 1
    
    # Standard business hours: Mon-Fri 9-5, Closed weekends
    schedule = {
        0: (time(9, 0), time(17, 0)),      # Monday
        1: (time(9, 0), time(17, 0)),      # Tuesday
        2: (time(9, 0), time(17, 0)),      # Wednesday
        3: (time(9, 0), time(17, 0)),      # Thursday
        4: (time(9, 0), time(17, 0)),      # Friday
        # Saturday and Sunday: closed
    }

    for day, (start, end) in schedule.items():
        slot = AvailabilityService.set_doctor_working_hours(
            doctor_id=doctor_id,
            day_of_week=day,
            start_time=start,
            end_time=end,
            db=db
        )
        day_name = AvailabilityService.get_day_name(day)
        print(f"✓ {day_name}: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")

    print("\nSchedule setup complete!")


def demo_view_schedule(db: Session):
    """View doctor's schedule."""
    print("\n=== Doctor's Complete Schedule ===\n")

    doctor_id = 1
    schedule = AvailabilityService.get_doctor_schedule(doctor_id, db)

    print(f"Doctor {doctor_id} Schedule:")
    for day_name in AvailabilityService.DAY_NAMES:
        if day_name in schedule:
            info = schedule[day_name]
            print(f"  {day_name:12} {info['start']} - {info['end']}")
        else:
            print(f"  {day_name:12} CLOSED")


def demo_check_availability(db: Session):
    """Check if appointments fall within working hours."""
    print("\n=== Checking Appointment Availability ===\n")

    doctor_id = 1
    
    test_cases = [
        {
            "name": "Monday 10:00 AM (valid)",
            "datetime": datetime(2024, 3, 18, 10, 0),  # Monday
            "duration": 30
        },
        {
            "name": "Monday 16:45 (extends past hours)",
            "datetime": datetime(2024, 3, 18, 16, 45),  # Monday
            "duration": 30
        },
        {
            "name": "Saturday (no hours scheduled)",
            "datetime": datetime(2024, 3, 23, 10, 0),  # Saturday
            "duration": 30
        },
        {
            "name": "Friday 17:00 exactly (at boundary)",
            "datetime": datetime(2024, 3, 22, 17, 0),  # Friday
            "duration": 30
        },
        {
            "name": "Tuesday 14:00 (valid)",
            "datetime": datetime(2024, 3, 19, 14, 0),  # Tuesday
            "duration": 60
        },
    ]

    for test in test_cases:
        is_available, message = AvailabilityService.is_appointment_within_working_hours(
            doctor_id=doctor_id,
            appointment_start=test["datetime"],
            duration_minutes=test["duration"],
            db=db
        )

        status = "✓ AVAILABLE" if is_available else "✗ NOT AVAILABLE"
        print(f"{status:18} - {test['name']}")
        if message:
            print(f"                    Reason: {message}")
        print()


def demo_appointment_validation(db: Session):
    """Show full appointment validation including availability."""
    print("\n=== Full Appointment Validation ===\n")

    doctor_id = 1
    patient_id = 1
    
    # Valid appointment
    print("Scenario 1: Valid appointment (Mon 10:30, 1 hour)")
    print("-" * 50)
    test_rdv = {
        "date": datetime(2024, 3, 18, 10, 30),
        "duration_minutes": 60
    }

    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()

    if doctor and patient:
        try:
            # Check overlap first
            overlap = RendezVousService.check_overlap_with_duration(
                doctor_id=doctor_id,
                start_time=test_rdv["date"],
                duration_minutes=test_rdv["duration_minutes"],
                db=db,
                exclude_rdv_id=None
            )
            print(f"✓ No overlapping appointments: {overlap is None}")

            # Check availability
            availability_check = RendezVousService.is_within_availability(
                doctor=doctor,
                appointment_start=test_rdv["date"],
                duration_minutes=test_rdv["duration_minutes"],
                db=db
            )
            print(f"✓ Within working hours: {availability_check['is_available']}")
            if not availability_check['is_available']:
                print(f"  Reason: {availability_check['reason']}")

        except Exception as e:
            print(f"✗ Validation failed: {e}")
    else:
        print("Doctor or Patient not found in database")

    # Invalid appointment (outside hours)
    print("\nScenario 2: Invalid appointment (Saturday 10:30, 1 hour)")
    print("-" * 50)
    test_rdv2 = {
        "date": datetime(2024, 3, 23, 10, 30),  # Saturday
        "duration_minutes": 60
    }

    try:
        availability_check = RendezVousService.is_within_availability(
            doctor=doctor,
            appointment_start=test_rdv2["date"],
            duration_minutes=test_rdv2["duration_minutes"],
            db=db
        )
        print(f"✗ Within working hours: {availability_check['is_available']}")
        print(f"  Reason: {availability_check['reason']}")

    except Exception as e:
        print(f"✗ Validation failed: {e}")


def main():
    """Run the demo."""
    print("\n" + "=" * 60)
    print("DOCTOR AVAILABILITY SYSTEM - DEMO")
    print("=" * 60)

    print("\nNOTE: This is a demonstration script showing how the system works.")
    print("To run with actual database, pass a database session.")
    print("\nKey features demonstrated:")
    print("  1. Setup doctor's weekly working hours")
    print("  2. View doctor's complete schedule")
    print("  3. Check if specific appointments fit within working hours")
    print("  4. Full appointment validation including availability")
    print("\nImplementation includes:")
    print("  ✓ Day of week based scheduling (0=Monday, 6=Sunday)")
    print("  ✓ Time-based working hours (start_time, end_time)")
    print("  ✓ Overlap detection for appointments")
    print("  ✓ Rejection of appointments outside working hours")
    print("  ✓ Integration with existing rendezvous validation")


if __name__ == "__main__":
    main()
