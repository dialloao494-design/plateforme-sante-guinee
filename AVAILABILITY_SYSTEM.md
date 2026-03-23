# Doctor Availability System - Implementation Guide

## Overview

The doctor availability system manages recurring weekly working hours for doctors and validates that appointments are booked within those working hours.

## Architecture

### Components

1. **Model** (`models/availability.py`)
   - `DoctorAvailability`: Stores doctor's working hours per day of week
   - Fields: `doctor_id`, `day_of_week` (0-6), `start_time`, `end_time`, `is_active`

2. **Schema** (`schemas/availability.py`)
   - `DoctorAvailabilityCreate`: For creating availability slots
   - `DoctorAvailabilityResponse`: For API responses
   - `DoctorAvailabilityUpdate`: For updating availability slots

3. **Router** (`routers/doctor.py`)
   - CRUD endpoints for managing doctor availability
   - Schedule viewing endpoint

4. **Services**
   - `rendezvous_service.py`: Core appointment validation (includes availability checking)
   - `availability_service.py`: Helper utilities for availability management

## API Endpoints

### Create Working Hours
```
POST /doctors/{doctor_id}/availability
Authorization: admin, doctor

Body:
{
  "doctor_id": 1,
  "day_of_week": 0,  # 0=Monday, 6=Sunday
  "start_time": "09:00:00",
  "end_time": "17:00:00"
}
```

### Get Doctor Schedule
```
GET /doctors/{doctor_id}/schedule
Authorization: admin, doctor, patient

Response:
{
  "doctor_id": 1,
  "doctor_name": "Dr. Smith",
  "schedule": {
    "Monday": {"start": "09:00", "end": "17:00", "id": 1, "is_active": true},
    "Wednesday": {"start": "09:00", "end": "17:00", "id": 2, "is_active": true},
    ...
  }
}
```

### Get All Availability Slots
```
GET /doctors/{doctor_id}/availability
Authorization: admin, doctor, patient

Response: List of DoctorAvailabilityResponse objects
```

### Update Availability Slot
```
PUT /doctors/{doctor_id}/availability/{availability_id}
Authorization: admin, doctor

Body: (all fields optional)
{
  "day_of_week": 1,
  "start_time": "10:00:00",
  "end_time": "18:00:00",
  "is_active": true
}
```

### Delete Availability Slot
```
DELETE /doctors/{doctor_id}/availability/{availability_id}
Authorization: admin, doctor

Response: {"detail": "Availability slot disabled"}
```

## Integration with Appointment Booking

When a patient books an appointment:

1. **Validation Flow**:
   - Appointment date/time is parsed
   - Day of week is extracted
   - Doctor's availability for that day is checked
   - Appointment time must fall within working hours
   - Appointment end time must not exceed working hours end

2. **Overlap Detection** (still works):
   - Existing appointments for the doctor are checked
   - Time slots cannot overlap with confirmed/pending appointments

3. **Error Messages**:
   - "Doctor has no working hours scheduled for Monday"
   - "Appointment 14:00-15:00 outside working hours 09:00-17:00"

## Usage Examples

### Setup Doctor Schedule (Python)
```python
from datetime import time
from services.availability_service import AvailabilityService

# Set Monday 09:00-17:00
AvailabilityService.set_doctor_working_hours(
    doctor_id=1,
    day_of_week=0,  # Monday
    start_time=time(9, 0),
    end_time=time(17, 0),
    db=session
)

# Set Wednesday 10:00-18:00
AvailabilityService.set_doctor_working_hours(
    doctor_id=1,
    day_of_week=2,  # Wednesday
    start_time=time(10, 0),
    end_time=time(18, 0),
    db=session
)
```

### Check Appointment Availability (Python)
```python
from datetime import datetime, time
from services.availability_service import AvailabilityService

appointment_start = datetime(2024, 3, 18, 14, 30)  # Monday 14:30
duration = 30  # minutes

is_available, message = AvailabilityService.is_appointment_within_working_hours(
    doctor_id=1,
    appointment_start=appointment_start,
    duration_minutes=duration,
    db=session
)

if is_available:
    print("Appointment can be booked")
else:
    print(f"Cannot book: {message}")
```

### Get Doctor's Weekly Schedule (Python)
```python
from services.availability_service import AvailabilityService

schedule = AvailabilityService.get_doctor_schedule(doctor_id=1, db=session)
print(schedule)
# Output:
# {
#   'Monday': {'start': '09:00', 'end': '17:00', 'id': 1, 'is_active': True},
#   'Wednesday': {'start': '10:00', 'end': '18:00', 'id': 2, 'is_active': True}
# }
```

## Constraints & Validation

1. **Day of Week**: Must be 0-6 (0=Monday, 6=Sunday)
2. **Working Hours**: `end_time` must be after `start_time`
3. **No Duplicates**: Only one active availability slot per day per doctor
4. **Appointment Time**: Must fall completely within working hours (start >= working_start AND end <= working_end)
5. **No Overlap**: Appointments cannot overlap with existing confirmed/pending appointments

## Database Schema

```sql
CREATE TABLE doctor_availabilities (
  id INTEGER PRIMARY KEY,
  doctor_id INTEGER NOT NULL FOREIGN KEY,
  day_of_week INTEGER NOT NULL,  -- 0-6
  start_time TIME NOT NULL,      -- e.g., 09:00:00
  end_time TIME NOT NULL,        -- e.g., 17:00:00
  is_active BOOLEAN DEFAULT TRUE
);
```

## Implementation Notes

1. **Day of Week**: Uses Python's `datetime.weekday()` convention (0=Monday, 6=Sunday)
2. **Soft Delete**: Availability slots are deactivated (is_active=False) rather than hard deleted
3. **Overlapping Check**: Still uses exact time-slot overlap detection for appointments
4. **UTC Time**: All times are stored in database time (ensure proper timezone handling in application)

## Testing Appointments Against Availability

The appointment validation now includes:
1. ✅ Duration validation
2. ✅ Past date prevention
3. ✅ Doctor existence check
4. ✅ Overlap detection (between appointments)
5. ✅ Working hours validation (new!)

Example validation for Mon 14:30, 30min appointment with 09:00-17:00 hours:
- Day: Monday (matches availability)
- Start: 14:30 >= 09:00 ✓
- End: 15:00 <= 17:00 ✓
- Result: **VALID**

Example validation for Tue 18:00, 30min appointment with no Tuesday hours set:
- Day: Tuesday
- No availability slot for Tuesday
- Result: **REJECTED** - "Doctor has no working hours scheduled for Tuesday"

Example validation for Mon 16:45, 30min appointment with 09:00-17:00 hours:
- Day: Monday
- Start: 16:45 >= 09:00 ✓
- End: 17:15 > 17:00 ✗
- Result: **REJECTED** - "Appointment outside working hours"
