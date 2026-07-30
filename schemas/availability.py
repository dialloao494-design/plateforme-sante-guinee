from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import time


class DoctorAvailabilityBase(BaseModel):
    doctor_id: int
    day_of_week: int  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    start_time: time
    end_time: time

    @field_validator("day_of_week")
    @classmethod
    def validate_day_of_week(cls, v):
        if not 0 <= v <= 6:
            raise ValueError("day_of_week must be between 0 (Monday) and 6 (Sunday)")
        return v

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    pass


class DoctorAvailabilityResponse(DoctorAvailabilityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class DoctorAvailabilityUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_of_week: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    is_active: bool | None = None
