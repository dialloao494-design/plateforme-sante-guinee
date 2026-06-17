"""PEV / immunization schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class VaccineScheduleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vaccine_code: str
    vaccine_name: str
    dose_label: str
    age_months: int
    grace_days: int


class ImmunizationRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    vaccine_code: str
    vaccine_name: str
    administered_at: date
    dose_label: Optional[str] = None
    batch_number: Optional[str] = None
    notes: Optional[str] = None


class ImmunizationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    patient_id: int
    vaccine_code: str
    vaccine_name: str
    dose_label: Optional[str] = None
    batch_number: Optional[str] = None
    administered_at: date
    notes: Optional[str] = None
    created_at: datetime


class VaccineDueItem(BaseModel):
    vaccine_code: str
    vaccine_name: str
    dose_label: str
    age_months: int
    due_date: str


class ImmunizationStatusResponse(BaseModel):
    due: List[VaccineDueItem]
    missed: List[VaccineDueItem]
    upcoming: List[VaccineDueItem]
