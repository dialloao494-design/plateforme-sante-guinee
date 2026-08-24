"""Pydantic schemas for admission and hospitalization."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HospitalRoomCreate(BaseModel):
    ward_id: Optional[int] = None
    ward_name: Optional[str] = Field(None, min_length=1, max_length=128)
    room_number: str = Field(..., min_length=1, max_length=32)
    room_type: str = "general"
    capacity: int = Field(1, ge=1, le=20)
    notes: Optional[str] = None
    isolation_capable: bool = False
    accessible: bool = False
    sex_policy: str = Field("mixed", pattern="^(mixed|female|male|pediatric|newborn)$")

    @model_validator(mode="after")
    def require_ward(self):
        if self.ward_id is None and not self.ward_name:
            raise ValueError("ward_id is required")
        return self


class HospitalWardCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=128)
    service_type: str = Field("general", max_length=64)
    location: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None


class HospitalWardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    service_type: Optional[str] = Field(None, max_length=64)
    status: Optional[str] = Field(None, pattern="^(active|maintenance|closed)$")
    location: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None


class HospitalWardResponse(BaseModel):
    id: int
    clinic_id: int
    code: str
    name: str
    service_type: str
    status: str
    location: Optional[str]
    notes: Optional[str]
    room_count: int = 0
    bed_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class HospitalRoomUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(active|maintenance|closed)$")
    notes: Optional[str] = None
    room_type: Optional[str] = None


class HospitalRoomResponse(BaseModel):
    id: int
    clinic_id: int
    ward_id: Optional[int]
    ward_name: str
    room_number: str
    room_type: str
    capacity: int
    status: str
    notes: Optional[str]
    isolation_capable: bool = False
    accessible: bool = False
    sex_policy: str = "mixed"
    bed_count: int = 0
    occupied_beds: int = 0

    model_config = ConfigDict(from_attributes=True)


class HospitalBedCreate(BaseModel):
    bed_number: str = Field(..., min_length=1, max_length=32)
    accommodation_type: str = Field("regular_bed", pattern="^(regular_bed|cradle)$")
    pediatric_suitable: bool = False
    newborn_suitable: bool = False
    isolation_suitable: bool = False
    accessible: bool = False


class HospitalBedUpdate(BaseModel):
    status: str = Field(..., pattern="^(available|maintenance|unavailable)$")
    reason: Optional[str] = Field(None, max_length=500)
    expected_version: Optional[int] = Field(None, ge=1)


class HospitalBedResponse(BaseModel):
    id: int
    room_id: int
    bed_number: str
    stable_code: str
    accommodation_type: str
    pediatric_suitable: bool
    newborn_suitable: bool
    isolation_suitable: bool
    accessible: bool
    status: str
    status_reason: Optional[str] = None
    version: int
    reserved_for_admission_id: Optional[int] = None
    reserved_until: Optional[datetime] = None
    last_cleaned_at: Optional[datetime] = None
    ward_name: Optional[str] = None
    room_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdmissionCreate(BaseModel):
    consultation_id: Optional[int] = None
    patient_id: Optional[int] = None
    reason: Optional[str] = None
    diagnosis_summary: Optional[str] = None
    attending_clinician_user_id: Optional[int] = None
    notes: Optional[str] = None
    expected_discharge_at: Optional[datetime] = None
    placement_age_group: str = Field("adult", pattern="^(adult|pediatric|newborn)$")
    requires_isolation: bool = False
    requires_accessible: bool = False

    @model_validator(mode="after")
    def require_patient_or_consultation(self):
        if self.consultation_id is None and self.patient_id is None:
            raise ValueError("Either consultation_id or patient_id is required")
        return self


class AdmissionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|admitted|in_care|transferred|discharged|cancelled)$")
    outcome: Optional[str] = Field(
        None,
        pattern="^(cured|improved|unchanged|transferred|deceased|left_against_advice)$",
    )


class BedAssignmentRequest(BaseModel):
    bed_id: int
    transfer_reason: Optional[str] = None
    expected_bed_version: Optional[int] = Field(None, ge=1)
    suitability_override_reason: Optional[str] = Field(None, max_length=500)


class BedReservationRequest(BaseModel):
    admission_id: int
    reserved_until: datetime
    expected_bed_version: Optional[int] = Field(None, ge=1)


class BedStatusChangeRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)
    expected_version: Optional[int] = Field(None, ge=1)


class PatientStayResponse(BaseModel):
    id: int
    admission_id: int
    bed_id: int
    assigned_at: datetime
    released_at: Optional[datetime]
    is_current: bool
    transfer_reason: Optional[str]
    bed_number: Optional[str] = None
    room_number: Optional[str] = None
    ward_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdmissionResponse(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    consultation_id: Optional[int]
    admission_number: str
    status: str
    reason: Optional[str]
    diagnosis_summary: Optional[str]
    outcome: Optional[str] = None
    attending_clinician_user_id: Optional[int] = None
    attending_clinician_name: Optional[str] = None
    length_of_stay_days: Optional[float] = None
    notes: Optional[str]
    admitted_at: Optional[datetime]
    discharged_at: Optional[datetime]
    expected_discharge_at: Optional[datetime] = None
    placement_age_group: str = "adult"
    requires_isolation: bool = False
    requires_accessible: bool = False
    patient_name: Optional[str] = None
    current_bed: Optional[HospitalBedResponse] = None
    stays: List[PatientStayResponse] = []

    model_config = ConfigDict(from_attributes=True)


class OccupancySummary(BaseModel):
    total_beds: int
    available_beds: int
    occupied_beds: int
    maintenance_beds: int
    reserved_beds: int = 0
    cleaning_beds: int = 0
    unavailable_beds: int = 0
    occupancy_rate: float
    active_admissions: int
    pending_admissions: int


class HospitalizationDashboardStats(BaseModel):
    current_hospitalized: int
    admissions_this_month: int
    discharges_this_month: int
    average_length_of_stay_days: float
