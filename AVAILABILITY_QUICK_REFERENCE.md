# Doctor Availability System - Quick Reference

## Setup Doctor Working Hours (as Admin)

### Set Monday 9AM-5PM
```bash
curl -X POST http://localhost:8000/doctors/1/availability \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "doctor_id": 1,
    "day_of_week": 0,
    "start_time": "09:00:00",
    "end_time": "17:00:00"
  }'
```

### Set Tuesday 10AM-6PM
```bash
curl -X POST http://localhost:8000/doctors/1/availability \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "doctor_id": 1,
    "day_of_week": 1,
    "start_time": "10:00:00",
    "end_time": "18:00:00"
  }'
```

## View Doctor Schedule

### Get Full Weekly Schedule
```bash
curl -X GET http://localhost:8000/doctors/1/schedule \
  -H "Authorization: Bearer <token>"
```

Response:
```json
{
  "doctor_id": 1,
  "doctor_name": "Dr. Smith",
  "schedule": {
    "Monday": {"start": "09:00", "end": "17:00"},
    "Tuesday": {"start": "10:00", "end": "18:00"},
    "Wednesday": {"start": "09:00", "end": "17:00"},
    ...
  }
}
```

### Get All Availability Slots
```bash
curl -X GET http://localhost:8000/doctors/1/availability \
  -H "Authorization: Bearer <token>"
```

## Update Availability

### Change Wednesday to 8AM-4PM
```bash
# First, get the slot ID
curl -X GET http://localhost:8000/doctors/1/availability

# Then update it (assuming ID is 3)
curl -X PUT http://localhost:8000/doctors/1/availability/3 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin-token>" \
  -d '{
    "start_time": "08:00:00",
    "end_time": "16:00:00"
  }'
```

## Deactivate a Day

### Close Doctor on Friday
```bash
curl -X DELETE http://localhost:8000/doctors/1/availability/5 \
  -H "Authorization: Bearer <admin-token>"
```

## Python Usage Examples

### In Your Application Code

```python
from datetime import datetime, time
from services.availability_service import AvailabilityService

# Check if appointment can be booked
appointment_time = datetime(2024, 3, 18, 14, 30)  # Monday 2:30 PM
is_available, reason = AvailabilityService.is_appointment_within_working_hours(
    doctor_id=1,
    appointment_start=appointment_time,
    duration_minutes=60,
    db=session
)

if is_available:
    # Book the appointment
    pass
else:
    # Show error to patient
    print(f"Cannot book: {reason}")

# Get doctor's schedule
schedule = AvailabilityService.get_doctor_schedule(doctor_id=1, db=session)
for day, times in schedule.items():
    print(f"{day}: {times['start']}-{times['end']}")
```

## Day of Week Reference

| Number | Day |
|--------|-----|
| 0 | Monday |
| 1 | Tuesday |
| 2 | Wednesday |
| 3 | Thursday |
| 4 | Friday |
| 5 | Saturday |
| 6 | Sunday |

## Common Scenarios

### Scenario: Book 30-min appointment Monday at 3:00 PM
**Doctor works:** 9:00 AM - 5:00 PM Monday
**Appointment:** 3:00 PM - 3:30 PM
**Result:** ✅ VALID (3:30 PM ≤ 5:00 PM)

### Scenario: Book 30-min appointment Monday at 4:45 PM
**Doctor works:** 9:00 AM - 5:00 PM Monday
**Appointment:** 4:45 PM - 5:15 PM
**Result:** ❌ INVALID (5:15 PM > 5:00 PM)

### Scenario: Book 1-hour appointment Tuesday (no schedule set)
**Doctor works:** No availability set
**Appointment:** Tuesday any time
**Result:** ❌ INVALID ("Doctor has no working hours scheduled for Tuesday")

### Scenario: Book appointment on Saturday
**Doctor works:** Mon-Fri only
**Appointment:** Saturday any time
**Result:** ❌ INVALID ("Doctor has no working hours scheduled for Saturday")

## Validation Chain for Appointments

1. ✓ Duration is valid (30, 60, 90, 120 min)
2. ✓ Appointment is not in the past
3. ✓ Doctor exists
4. ✓ No overlapping confirmed/pending appointments
5. ✓ **NEW:** Appointment within doctor's working hours for that day
6. ✓ **NEW:** Appointment doesn't extend past working hours

All checks must pass for appointment creation.
