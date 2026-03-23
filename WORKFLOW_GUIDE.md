# Doctor Availability System - Complete Workflow

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND / CLIENT                         │
│  (Patient Portal, Admin Dashboard, Mobile App)               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ API Calls
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    ROUTER LAYER                              │
│  ┌─ /doctors/{id}/availability (CRUD)                        │
│  ├─ /doctors/{id}/schedule (View)                            │
│  ├─ /rendezvous (Create, Update, List)                       │
│  └─ /doctors/{id} (Create, Update, Delete)                   │
└────┬────────────────────────────────────┬────────────────────┘
     │                                    │
     ▼                                    ▼
┌──────────────────────┐        ┌──────────────────────┐
│    AVAILABILITY      │        │  RENDEZVOUS SERVICE  │
│     SERVICE          │        │    (Appointment)     │
│                      │        │                      │
│ - get_day_name()     │        │ - validate_appt()    │
│ - get_schedule()     │        │ - check_overlap()    │
│ - check_avail()      │◄──────►│ - is_within_avail()  │
│ - set_hours()        │        │ - create_appt()      │
│ - disable_day()      │        │ - update_status()    │
└──────────┬───────────┘        └──────────┬───────────┘
           │                               │
           └───────────┬───────────────────┘
                       │
                       ▼
          ┌────────────────────────────┐
          │   MODELS / DATABASE        │
          │                            │
          │ DoctorAvailability         │
          │ - id                       │
          │ - doctor_id                │
          │ - day_of_week (0-6)        │
          │ - start_time (TIME)        │
          │ - end_time (TIME)          │
          │ - is_active                │
          │                            │
          │ RendezVous                 │
          │ - id, date, duration       │
          │ - doctor_id, patient_id    │
          │ - status, timestamps       │
          └────────────────────────────┘
```

## Workflow: Setting Up Doctor Schedule

### Step 1: Admin Creates First Availability Slot

```
Admin Portal
    │
    ├─ Enter: Doctor ID=1, Day=Monday (0)
    ├─ Enter: Start=09:00, End=17:00
    │
    ▼
POST /doctors/1/availability
{
  "doctor_id": 1,
  "day_of_week": 0,
  "start_time": "09:00:00",
  "end_time": "17:00:00"
}
    │
    ▼
Router: create_doctor_availability()
    │
    ├─ Validate doctor_id matches path
    ├─ Validate doctor exists
    ├─ Check no duplicate slot for day_of_week (✓)
    │
    ▼
AvailabilityService: validate_working_hours()
    └─ Verify: end_time > start_time ✓
    
    ▼
Database INSERT
    │
    ▼
202 Created
{
  "id": 1,
  "doctor_id": 1,
  "day_of_week": 0,
  "start_time": "09:00:00",
  "end_time": "17:00:00",
  "is_active": true
}
```

### Step 2: Admin Sets Full Weekly Schedule

```
For each day Monday-Friday:
  POST /doctors/1/availability (with day 0, 1, 2, 3, 4)
  ├─ Creates 5 availability slots, one per weekday
  └─ Stored as 5 separate records in database
  
Saturday & Sunday:
  │
  └─ NOT created
     (no availability = closed)
```

## Workflow: Booking an Appointment

### Step 1: Patient Checks Availability

```
Patient Portal
    │
    ├─ View available doctors
    ├─ Select Dr. Smith (doctor_id=1)
    ├─ Select date: Monday, March 18
    ├─ Select time: 2:30 PM (14:30)
    ├─ Duration: 30 minutes
    │
    ▼
GET /doctors/1/schedule
    │
    ▼
Response: {
  "doctor_id": 1,
  "schedule": {
    "Monday": {"start": "09:00", "end": "17:00"},
    "Tuesday": {"start": "09:00", "end": "17:00"},
    ...
  }
}
    │
    ▼
Patient sees: Monday 09:00-17:00 ✓ Available for 14:30
```

### Step 2: Patient Books Appointment

```
Patient clicks: "Book at 14:30 on Monday"
    │
    ▼
POST /rendezvous/
{
  "date": "2024-03-18T14:30:00",
  "duration_minutes": 30,
  "doctor_id": 1,
  "patient_id": 5
}
    │
    ▼
Router: create_rendezvous()
    │
    ▼
RendezVousService.validate_appointment()
    │
    ├─ Check 1: Duration valid (30, 60, 90, 120)? ✓ 30
    │
    ├─ Check 2: Not in past? ✓ 2024-03-18 is future
    │
    ├─ Check 3: Doctor exists? ✓ Dr. Smith found
    │
    ├─ Check 4: No overlapping appointments?
    │   └─ Query appointments for doctor_id=1
    │   └─ For this doctor, any status != 'cancelled'
    │   └─ No appointments 14:30-15:00? ✓ Clear
    │
    ├─ Check 5: **NEW** Within working hours?
    │   │
    │   ├─ Extract: appointment.day_of_week = Monday (0)
    │   ├─ Extract: appointment.start_time = 14:30
    │   ├─ Calculate: appointment.end_time = 15:00
    │   │
    │   └─ Query: DoctorAvailability
    │       WHERE doctor_id=1 AND day_of_week=0 AND is_active=true
    │       RESULT: start=09:00, end=17:00
    │   │
    │   ├─ Check: 09:00 <= 14:30? ✓ Yes
    │   ├─ Check: 15:00 <= 17:00? ✓ Yes
    │   └─ Result: AVAILABLE ✓
    │
    └─ All checks passed ✓
    
    ▼
Create appointment record
    │
    ▼
202 Created
{
  "id": 42,
  "date": "2024-03-18T14:30:00",
  "duration_minutes": 30,
  "doctor_id": 1,
  "patient_id": 5,
  "status": "pending",
  "created_at": "2024-03-17T10:00:00"
}
    │
    ▼
Patient sees: "✓ Appointment confirmed! Monday 2:30 PM"
```

### Step 3: Failed Booking (Outside Hours)

```
Patient tries: Saturday 10:00 AM
    │
    ▼
POST /rendezvous/
{
  "date": "2024-03-23T10:00:00",  ← Saturday
  "duration_minutes": 30,
  "doctor_id": 1,
  "patient_id": 5
}
    │
    ▼
RendezVousService.validate_appointment()
    │
    ├─ Checks 1-4: All pass
    │
    ├─ Check 5: Within working hours?
    │   │
    │   ├─ Extract: appointment.day_of_week = Saturday (5)
    │   │
    │   └─ Query: DoctorAvailability
    │       WHERE doctor_id=1 AND day_of_week=5 AND is_active=true
    │       RESULT: Not found
    │   │
    │   └─ Result: NOT AVAILABLE ✗
    │
    └─ Raising HTTPException(400)
    
    ▼
400 Bad Request
{
  "detail": "No availability for doctor at this time. Doctor has no working hours scheduled for Saturday"
}
    │
    ▼
Patient sees: "❌ Doctor is not available on Saturday"
```

## Workflow: Updating Doctor Schedule

### Scenario: Doctor Wants to Close Early on Tuesday

```
Admin Portal
    │
    ├─ Find availability slot for Tuesday (id=2)
    │
    ▼
PUT /doctors/1/availability/2
{
  "end_time": "16:00:00"  ← Changed from 17:00
}
    │
    ▼
Router: update_doctor_availability()
    │
    ├─ Find slot id=2 for doctor_id=1 ✓
    │
    ├─ Update: end_time = 16:00
    │
    ├─ Validate: end_time > start_time? ✓ 16:00 > 09:00
    │
    ▼
Database UPDATE
    │
    ▼
200 OK
{
  "id": 2,
  "doctor_id": 1,
  "day_of_week": 1,
  "start_time": "09:00:00",
  "end_time": "16:00:00",  ← Updated
  "is_active": true
}
    │
    ▼
New bookings on Tuesday can't exceed 16:00
(Existing appointments unaffected)
```

## Data Flow During Appointment Creation

```
INPUT:
date = 2024-03-18 14:30
duration = 30 min
doctor_id = 1

EXTRACTION:
day_of_week = datetime.weekday() = 0 (Monday)
start_time = 14:30
end_time = 15:00

DATABASE QUERIES:
1. SELECT Doctor WHERE id=1 → Found
2. SELECT RendezVous WHERE doctor_id=1 AND status!='cancelled' 
   → Check overlap with [14:30, 15:00] → None found
3. SELECT DoctorAvailability 
   WHERE doctor_id=1 AND day_of_week=0 AND is_active=true
   → Slot: start_time=09:00, end_time=17:00
   → Found

VALIDATION LOGIC:
✓ 09:00 <= 14:30 (start within hours)
✓ 15:00 <= 17:00 (end within hours)

RESULT: APPROVED → Insert RendezVous record
```

## Key Decision Points

```
┌─ Appointment Request
│
├─ Is duration valid? ──NO──> 400 Bad Request
├─ Is in past? ──YES──> 400 Bad Request
├─ Does doctor exist? ──NO──> 404 Not Found
├─ Overlaps existing? ──YES──> 409 Conflict
├─ Is within working hours? ──NO──> 400 Bad Request
│                          │
│                          YES
│                          │
├─ All checks passed ──────────────────────────┐
│                                              │
└──────────────► CREATE APPOINTMENT            │
                                              │
                                              ▼
                                    202 Created
                                    {appointment}
```

## Integration with Existing System

```
Before: Only checked if date was in future + overlap
After:  Also checks if time fits within weekly working hours

┌─────────────────────────────────────────┐
│  VALIDATION CHAIN FOR APPOINTMENTS       │
├─────────────────────────────────────────┤
│ 1. Duration valid? (existing)            │
│ 2. Not in past? (existing)               │
│ 3. Doctor exists? (existing)             │
│ 4. No overlap? (existing)                │
│ 5. Within working hours? (NEW) ◄─────────┤
│                                          │
│    → Can only book during doctor        │
│      working hours for that day         │
│    → Prevents off-hours booking         │
│    → Rejects unavailable days           │
└─────────────────────────────────────────┘
```

## Error Scenarios

```
Scenario 1: Booking outside working hours
Error: "Appointment 18:00-18:30 outside working hours 09:00-17:00"

Scenario 2: Booking on unavailable day
Error: "Doctor has no working hours scheduled for Saturday"

Scenario 3: Booking overlaps existing appointment
Error: "Time slot conflicts with existing appointment (ID: 5, starts 2024-03-18T14:00:00, duration 30 min)"
(This is the EXISTING overlap detection, works with new system)

Scenario 4: Duration too long
Error: "Invalid duration. Must be one of: [30, 60, 90, 120]"

Scenario 5: Doctor not found
Error: "Doctor not found"
```

## Query Performance Notes

- **Doctor Schedule**: 7 queries max (1 per day) - very fast ✓
- **Appointment Validation**: 3 queries (doctor + overlaps + availability) - efficient ✓
- **Weekly Schedule**: Single query with order by day_of_week - fast ✓
- **Index Recommendations**: 
  - `doctor_availabilities(doctor_id, day_of_week, is_active)`
  - `rendezvous(doctor_id, status)` (already likely exists)
