"""Pydantic schemas for admission and hospitalization."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class HospitalRoomCreate(BaseModel):
    ward_name: str = Field(..., min_length=1, max_length=128)
    room_number: str = Field(..., min_length=1, max_length=32)
    room_type: str = "general"
    capacity: int = Field(1, ge=1, le=20)
    notes: Optional[str] = None


class HospitalRoomResponse(BaseModel):
    id: int
    clinic_id: int
    ward_name: str
    room_number: str
    room_type: str
    capacity: int
    status: str
    notes: Optional[str]
    bed_count: int = 0
    occupied_beds: int = 0

    class Config:
        from_attributes = True


class HospitalBedCreate(BaseModel):
    bed_number: str = Field(..., min_length=1, max_length=32)


class HospitalBedResponse(BaseModel):
    id: int
    room_id: int
    bed_number: str
    status: str
    ward_name: Optional[str] = None
    room_number: Optional[str] = None

    class Config:
        from_attributes = True


class AdmissionCreate(BaseModel):
    consultation_id: int
    reason: Optional[str] = None
    diagnosis_summary: Optional[str] = None
    notes: Optional[str] = None


class AdmissionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|admitted|in_care|transferred|discharged|cancelled)$")


class BedAssignmentRequest(BaseModel):
    bed_id: int
    transfer_reason: Optional[str] = None


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

    class Config:
        from_attributes = True


class AdmissionResponse(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    consultation_id: Optional[int]
    admission_number: str
    status: str
    reason: Optional[str]
    diagnosis_summary: Optional[str]
    notes: Optional[str]
    admitted_at: Optional[datetime]
    discharged_at: Optional[datetime]
    patient_name: Optional[str] = None
    current_bed: Optional[HospitalBedResponse] = None
    stays: List[PatientStayResponse] = []

    class Config:
        from_attributes = True


class OccupancySummary(BaseModel):
    total_beds: int
    available_beds: int
    occupied_beds: int
    maintenance_beds: int
    occupancy_rate: float
    active_admissions: int
    pending_admissions: int
