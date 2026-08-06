"""Schemas for nurse triage / assessment."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def calc_bmi(weight_kg: Optional[float], height_cm: Optional[float]) -> Optional[float]:
    if weight_kg is None or height_cm is None or height_cm <= 0:
        return None
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m * height_m), 1)


class NurseAssessmentCreate(BaseModel):
    patient_id: int
    admission_id: Optional[int] = None
    appointment_id: Optional[int] = None
    consultation_id: Optional[int] = None

    temperature_c: Optional[float] = Field(None, ge=30.0, le=45.0)
    bp_systolic: Optional[int] = Field(None, ge=40, le=300)
    bp_diastolic: Optional[int] = Field(None, ge=20, le=200)
    heart_rate: Optional[int] = Field(None, ge=20, le=250)
    respiratory_rate: Optional[int] = Field(None, ge=5, le=60)
    spo2_percent: Optional[float] = Field(None, ge=50.0, le=100.0)
    muac_cm: Optional[float] = Field(None, ge=5.0, le=60.0)  # PB
    head_circumference_cm: Optional[float] = Field(None, ge=20.0, le=70.0)  # PC
    height_cm: Optional[float] = Field(None, ge=30.0, le=250.0)
    weight_kg: Optional[float] = Field(None, ge=0.5, le=500.0)
    vitals_observations: Optional[str] = Field(None, max_length=5000)

    reason_for_consultation: Optional[str] = Field(None, max_length=10000)
    history_of_present_illness: Optional[str] = Field(None, max_length=10000)
    medical_history: Optional[str] = Field(None, max_length=10000)
    surgical_history: Optional[str] = Field(None, max_length=10000)
    gynecological_history: Optional[str] = Field(None, max_length=10000)
    allergies: Optional[str] = Field(None, max_length=5000)
    current_treatments: Optional[str] = Field(None, max_length=10000)
    hospitalized_daily_vitals: Optional[str] = Field(None, max_length=10000)
    prescription: Optional[str] = Field(None, max_length=10000)
    nurse_notes: Optional[str] = Field(None, max_length=10000)

    @field_validator(
        "temperature_c",
        "bp_systolic",
        "bp_diastolic",
        "heart_rate",
        "respiratory_rate",
        "spo2_percent",
        "muac_cm",
        "head_circumference_cm",
        "height_cm",
        "weight_kg",
        mode="before",
    )
    @classmethod
    def _empty_vital_as_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            text = v.strip()
            if text in ("", "0", "0.0"):
                return None
            return text
        if isinstance(v, (int, float)) and v == 0:
            return None
        return v


class NurseAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    patient_id: int
    admission_id: Optional[int] = None
    appointment_id: Optional[int] = None
    consultation_id: Optional[int] = None
    nurse_user_id: Optional[int] = None
    nurse_name: Optional[str] = None

    temperature_c: Optional[float] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    heart_rate: Optional[int] = None
    respiratory_rate: Optional[int] = None
    spo2_percent: Optional[float] = None
    muac_cm: Optional[float] = None
    head_circumference_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    bmi: Optional[float] = None
    vitals_observations: Optional[str] = None

    reason_for_consultation: Optional[str] = None
    history_of_present_illness: Optional[str] = None
    medical_history: Optional[str] = None
    surgical_history: Optional[str] = None
    gynecological_history: Optional[str] = None
    allergies: Optional[str] = None
    current_treatments: Optional[str] = None
    hospitalized_daily_vitals: Optional[str] = None
    prescription: Optional[str] = None
    nurse_notes: Optional[str] = None

    recorded_at: datetime
    updated_at: datetime

    patient_number: Optional[str] = None
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None


class NurseDashboardStats(BaseModel):
    assessments_today: int = 0
    pending_admissions_today: int = 0
    recent_assessments: list[NurseAssessmentResponse] = []


class NursePatientDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_number: Optional[str] = None
    qr_token: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    date_of_birth_precision: Optional[str] = None
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    commune: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    profession: Optional[str] = None
    preferred_language: Optional[str] = None


class NurseAssessmentQueueRow(BaseModel):
    assessment_id: int
    patient_id: int
    patient_number: Optional[str] = None
    patient_name: str
    nurse_name: Optional[str] = None
    status: str = "Évalué"
    recorded_at: datetime


class NursePendingAdmissionRow(BaseModel):
    admission_id: int
    patient_id: int
    patient_number: Optional[str] = None
    patient_name: str
    admitted_at: Optional[datetime] = None
    services: list[str] = []
    priority: str = "Routine"
    department: Optional[str] = None
