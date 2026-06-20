"""PEV / immunization schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Dict

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
    dose_number: Optional[int] = Field(None, ge=1, le=10)
    batch_number: Optional[str] = None
    next_appointment_date: Optional[date] = None
    vaccinator_name: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None


class ImmunizationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    patient_id: int
    vaccine_code: str
    vaccine_name: str
    dose_label: Optional[str] = None
    dose_number: Optional[int] = None
    batch_number: Optional[str] = None
    administered_at: date
    next_appointment_date: Optional[date] = None
    vaccinator_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


class ImmunizationDashboardStats(BaseModel):
    daily_vaccinations: int
    monthly_vaccinations: int
    by_age_group: Dict[str, int]
    by_vaccine_type: Dict[str, int]


class ImmunizationMonthlyReport(BaseModel):
    year: int
    month: int
    total_vaccinations: int
    by_vaccine_type: Dict[str, int]
    by_age_group: Dict[str, int]
    records: List[ImmunizationRecordResponse]


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
