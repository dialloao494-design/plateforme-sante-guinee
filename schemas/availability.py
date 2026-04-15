from pydantic import BaseModel, validator
from datetime import time


class DoctorAvailabilityBase(BaseModel):
    doctor_id: int
    day_of_week: int  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    start_time: time
    end_time: time

    @validator("day_of_week")
    def validate_day_of_week(cls, v):
        if not 0 <= v <= 6:
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        return v

    @validator("end_time")
    def validate_times(cls, v, values):
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("end_time must be after start_time")
        return v


class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    pass


class DoctorAvailabilityResponse(DoctorAvailabilityBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class DoctorAvailabilityUpdate(BaseModel):
    day_of_week: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None

    class Config:
        from_attributes = True
