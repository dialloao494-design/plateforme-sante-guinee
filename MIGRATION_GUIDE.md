# Database Migration Guide

## Schema Changes

### Old Schema (DateTime-based)
```sql
CREATE TABLE doctor_availabilities (
  id INTEGER PRIMARY KEY,
  doctor_id INTEGER FOREIGN KEY,
  start_time DATETIME,  -- Absolute timestamps
  end_time DATETIME,    -- Absolute timestamps
  is_active BOOLEAN
);
```

### New Schema (Recurring day-based)
```sql
CREATE TABLE doctor_availabilities (
  id INTEGER PRIMARY KEY,
  doctor_id INTEGER FOREIGN KEY,
  day_of_week INTEGER,  -- 0-6: Monday-Sunday
  start_time TIME,      -- e.g., 09:00:00
  end_time TIME,        -- e.g., 17:00:00
  is_active BOOLEAN DEFAULT TRUE
);
```

## Key Differences

| Aspect | Old | New |
|--------|-----|-----|
| **Time Model** | Absolute (specific dates) | Recurring (weekly pattern) |
| **Storage** | DateTime (date + time) | Time only (HH:MM:SS) |
| **Flexibility** | One-time slots only | Repeating weekly pattern |
| **Use Case** | One-off appointments | Regular working hours |
| **Day Specification** | Implicit in DateTime | Explicit 0-6 |

## Migration Steps (If Applicable)

### Option 1: Fresh Database (Recommended for new deployments)
1. Delete existing `doctor_availabilities` table
2. Run migrations to create new schema
3. Populate with recurring weekly schedules

### Option 2: Data Migration (If you have existing availability data)

```python
from datetime import datetime, time
from sqlalchemy import text

# Assuming old table exists with DateTime fields
def migrate_availability_data(db_session):
    """
    Migrate from old DateTime-based to new recurring model.
    Note: This assumes you want to convert one-time slots to recurring weekly.
    """
    from models.availability import DoctorAvailability as NewDoctorAvailability
    import models
    
    # Get all old availability records
    old_records = db_session.execute(text("""
        SELECT id, doctor_id, start_time, end_time 
        FROM doctor_availabilities_old
    """)).fetchall()
    
    for record in old_records:
        doctor_id, start_datetime, end_datetime = (
            record[1], record[2], record[3]
        )
        
        # Extract day and times
        day_of_week = start_datetime.weekday()
        start_time = start_datetime.time()
        end_time = end_datetime.time()
        
        # Create new record
        new_slot = NewDoctorAvailability(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        db_session.add(new_slot)
    
    db_session.commit()
```

## Breaking Changes

### 1. API Schema Changed

**Old:**
```json
{
  "doctor_id": 1,
  "start_time": "2024-03-18T09:00:00",
  "end_time": "2024-03-18T17:00:00"
}
```

**New:**
```json
{
  "doctor_id": 1,
  "day_of_week": 0,
  "start_time": "09:00:00",
  "end_time": "17:00:00"
}
```

### 2. Availability Logic Changed

**Old:** Exact DateTime matching
- Appointment had to fall exactly between start_time and end_time on that date

**New:** Recurring weekly + daily time range
- Appointment day must match the day_of_week (0-6)
- Appointment time must fall between start_time and end_time

### 3. Multiple Slots Per Day

**Old:** Could have multiple DateTime slots per doctor
**New:** Only ONE slot per day_of_week per doctor

## Affected Endpoints

| Old Endpoint | Changes | Status |
|--------------|---------|--------|
| POST /doctors/{id}/availability | Schema changed | ⚠️ Breaking |
| GET /doctors/{id}/availability | Response schema changed | ⚠️ Breaking |
| PUT /doctors/{id}/availability/{id} | NEW endpoint | ✨ Added |
| DELETE /doctors/{id}/availability/{id} | Same, now soft-delete | ✓ Compatible |
| GET /doctors/{id}/schedule | NEW endpoint | ✨ Added |

## Service Layer Changes

### RendezVousService.is_within_availability()

**Old Logic:**
```python
# Checked: start_time <= appointment_start AND appointment_end <= end_time
# (absolute DateTime comparison)
```

**New Logic:**
```python
# Checks:
# 1. appointment.day_of_week matches availability.day_of_week
# 2. availability.start_time <= appointment.start_time.time()
# 3. appointment.end_time.time() <= availability.end_time
```

## Testing Recommendations

1. **Unit Tests:** Test new day_of_week logic with various day combinations
2. **Integration Tests:** Test appointment creation against new availability rules
3. **Edge Cases:**
   - Appointments spanning midnight (shouldn't happen but handle gracefully)
   - Boundary conditions (appointment exactly at working hours end)
   - Missing availability slots

## Rollback Plan

If needed to revert:
1. Keep old `doctor_availabilities` table as backup
2. Export new data back to old DateTime format
3. Revert code to old service logic
4. Update API clients

## Documentation Updates

Update API documentation to reflect:
- New day_of_week field (0-6)
- Time-only fields (not DateTime)
- Weekly recurring pattern
- Example schedules for 9-5, 10-6, custom hours

## Client-Side Updates

Any clients calling the API need to update to:
1. Send `day_of_week` instead of absolute dates
2. Send `time` fields instead of `datetime`
3. Handle new error messages about missing days/outside hours

## Benefits of New System

✅ Simpler to manage recurring schedules
✅ More scalable (one record per day, not per date)
✅ Better for most use cases (doctors have weekly patterns)
✅ Clearer business logic (appointments vs. recurring hours)
✅ Easier to query availability by day
✅ Supports different hours per day of week naturally
