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
    vaccine_expiry_date: Optional[date] = None
    injection_site: Optional[str] = Field(None, max_length=64)
    vaccination_strategy: Optional[str] = Field("routine", max_length=32)
    next_appointment_date: Optional[date] = None
    vaccinator_name: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None
    aefi_notes: Optional[str] = None


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
    vaccine_expiry_date: Optional[date] = None
    injection_site: Optional[str] = None
    vaccination_strategy: Optional[str] = None
    age_at_vaccination_months: Optional[int] = None
    age_at_vaccination_days: Optional[int] = None
    administered_at: date
    next_appointment_date: Optional[date] = None
    vaccinator_name: Optional[str] = None
    notes: Optional[str] = None
    aefi_notes: Optional[str] = None
    created_at: datetime


class ImmunizationPatientSnapshot(BaseModel):
    """Patient demographics for registre PEV rows (single central patient record)."""

    id: int
    first_name: str
    last_name: str
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    age_display: Optional[str] = None
    mother_or_guardian: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


class ImmunizationRegisterRow(BaseModel):
    """One line of the monthly PEV register (registre papier)."""

    line_number: int
    record: ImmunizationRecordResponse
    patient: ImmunizationPatientSnapshot


class ImmunizationDashboardStats(BaseModel):
    daily_vaccinations: int
    monthly_vaccinations: int
    by_age_group: Dict[str, int]
    by_vaccine_type: Dict[str, int]
    by_strategy: Dict[str, int] = Field(default_factory=dict)


class ImmunizationMonthlyReport(BaseModel):
    year: int
    month: int
    clinic_id: int
    total_vaccinations: int
    by_vaccine_type: Dict[str, int]
    by_age_group: Dict[str, int]
    by_strategy: Dict[str, int]
    register_rows: List[ImmunizationRegisterRow]


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
