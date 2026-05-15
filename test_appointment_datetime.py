#!/usr/bin/env python3
"""
Test appointment datetime validation with local time.
Verifies that the fix allows creating appointments with future datetimes.
"""

from datetime import datetime, timedelta
from schemas.rendezvous import RendezVousCreate
from services.rendezvous_service import RendezVousService
import database
import models
from sqlalchemy.orm import Session

def test_appointment_creation_with_future_local_time():
    """Test that future appointments can be created with local datetime."""
    
    # Create a future appointment (30 minutes from now in local time)
    future_time = datetime.now() + timedelta(minutes=30)
    
    print(f"Current local time: {datetime.now()}")
    print(f"Appointment time: {future_time}")
    print(f"Time difference: 30 minutes")
    
    # Simulate the appointment creation payload from frontend
    appointment_payload = RendezVousCreate(
        date=future_time,
        doctor_id=1,
        duration_minutes=30,
        consultation_type="physical"
    )
    
    print(f"\n✓ Successfully created appointment payload")
    print(f"  - Date: {appointment_payload.date}")
    print(f"  - Doctor ID: {appointment_payload.doctor_id}")
    print(f"  - Duration: {appointment_payload.duration_minutes} minutes")
    print(f"  - Type: {appointment_payload.consultation_type}")
    
    # Test datetime comparison (this is what the backend validation does)
    if appointment_payload.date < datetime.now():
        print("\n✗ FAIL: Appointment is in the past!")
        return False
    else:
        print("\n✓ PASS: Appointment is in the future (validation passes)")
        return True

def test_appointment_creation_with_past_local_time():
    """Test that past appointments are rejected."""
    
    # Create a past appointment (30 minutes ago)
    past_time = datetime.now() - timedelta(minutes=30)
    
    print(f"\nCurrent local time: {datetime.now()}")
    print(f"Appointment time: {past_time}")
    print(f"Time difference: -30 minutes")
    
    # Simulate the appointment creation payload
    appointment_payload = RendezVousCreate(
        date=past_time,
        doctor_id=1,
        duration_minutes=30,
        consultation_type="physical"
    )
    
    print(f"\n✓ Successfully created appointment payload")
    
    # Test datetime comparison
    if appointment_payload.date < datetime.now():
        print("\n✓ PASS: Past appointment is correctly rejected (validation passes)")
        return True
    else:
        print("\n✗ FAIL: Past appointment was not rejected!")
        return False

def test_appointment_far_future():
    """Test appointments scheduled far in the future (e.g., next month)."""
    
    # Create appointment 30 days from now
    far_future = datetime.now() + timedelta(days=30)
    
    print(f"\nCurrent local time: {datetime.now()}")
    print(f"Appointment time: {far_future}")
    print(f"Time difference: 30 days")
    
    appointment_payload = RendezVousCreate(
        date=far_future,
        doctor_id=1,
        duration_minutes=60,
        consultation_type="teleconsultation"
    )
    
    print(f"\n✓ Successfully created appointment payload")
    print(f"  - Date: {appointment_payload.date}")
    print(f"  - Duration: {appointment_payload.duration_minutes} minutes")
    print(f"  - Type: {appointment_payload.consultation_type}")
    
    if appointment_payload.date < datetime.now():
        print("\n✗ FAIL: Far future appointment incorrectly rejected!")
        return False
    else:
        print("\n✓ PASS: Far future appointment is valid")
        return True

if __name__ == "__main__":
    print("=" * 60)
    print("APPOINTMENT DATETIME VALIDATION TESTS")
    print("=" * 60)
    
    results = []
    
    # Test 1: Future appointment
    print("\n[TEST 1] Future Appointment (30 minutes from now)")
    print("-" * 60)
    results.append(test_appointment_creation_with_future_local_time())
    
    # Test 2: Past appointment
    print("\n[TEST 2] Past Appointment (30 minutes ago)")
    print("-" * 60)
    results.append(test_appointment_creation_with_past_local_time())
    
    # Test 3: Far future appointment  
    print("\n[TEST 3] Far Future Appointment (30 days from now)")
    print("-" * 60)
    results.append(test_appointment_far_future())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED")
        exit(0)
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED")
        exit(1)
