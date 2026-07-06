"""Schemas for permanent medical history and follow-up tracking."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

FOLLOW_UP_INTERVALS = Literal["7d", "15d", "1m", "3m", "6m", "custom"]
FOLLOW_UP_VISIT_TYPES = Literal["consultation", "follow_up"]


class PatientMedicalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    blood_type: Optional[str] = None
    general_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PatientMedicalRecordUpdate(BaseModel):
    blood_type: Optional[str] = Field(None, max_length=8)
    general_notes: Optional[str] = Field(None, max_length=10000)


class PatientAllergyCreate(BaseModel):
    allergen: str = Field(..., min_length=1, max_length=255)
    severity: str = Field(default="moderate", max_length=32)
    reaction: Optional[str] = Field(None, max_length=2000)


class PatientAllergyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    allergen: str
    severity: str
    reaction: Optional[str] = None
    is_active: bool
    created_at: datetime


class PatientChronicConditionCreate(BaseModel):
    condition_name: str = Field(..., min_length=1, max_length=255)
    diagnosed_at: Optional[date] = None
    status: str = Field(default="active", max_length=32)
    notes: Optional[str] = Field(None, max_length=5000)


class PatientChronicConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    condition_name: str
    diagnosed_at: Optional[date] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime


class PatientVitalSignsCreate(BaseModel):
    consultation_id: Optional[int] = None
    bp_systolic: Optional[int] = Field(None, ge=40, le=300)
    bp_diastolic: Optional[int] = Field(None, ge=20, le=200)
    heart_rate: Optional[int] = Field(None, ge=20, le=250)
    temperature_c: Optional[float] = Field(None, ge=30.0, le=45.0)
    weight_kg: Optional[float] = Field(None, ge=0.5, le=500.0)
    height_cm: Optional[float] = Field(None, ge=30.0, le=250.0)
    respiratory_rate: Optional[int] = Field(None, ge=5, le=60)
    bmi: Optional[float] = Field(None, ge=10.0, le=80.0)
    spo2: Optional[int] = Field(None, ge=50, le=100)
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator(
        "bp_systolic",
        "bp_diastolic",
        "heart_rate",
        "temperature_c",
        "weight_kg",
        "height_cm",
        "respiratory_rate",
        "bmi",
        "spo2",
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


class PatientVitalSignsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    consultation_id: Optional[int] = None
    bp_systolic: Optional[int] = None
    bp_diastolic: Optional[int] = None
    heart_rate: Optional[int] = None
    temperature_c: Optional[float] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    respiratory_rate: Optional[int] = None
    bmi: Optional[float] = None
    spo2: Optional[int] = None
    notes: Optional[str] = None
    recorded_at: datetime


class FollowUpScheduleCreate(BaseModel):
    interval_type: FOLLOW_UP_INTERVALS
    scheduled_date: Optional[date] = None  # required when interval_type=custom
    visit_type: FOLLOW_UP_VISIT_TYPES = "follow_up"
    reason: Optional[str] = Field(None, max_length=2000)
    clinical_notes: Optional[str] = Field(None, max_length=5000)


class FollowUpScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    clinic_id: int
    consultation_id: Optional[int] = None
    doctor_id: int
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None
    scheduled_date: date
    interval_type: str
    visit_type: str
    reason: Optional[str] = None
    clinical_notes: Optional[str] = None
    status: str
    follow_up_appointment_id: Optional[int] = None
    created_at: datetime


class FollowUpReceptionSummary(BaseModel):
    due_today: list[FollowUpScheduleResponse]
    overdue: list[FollowUpScheduleResponse]
    upcoming: list[FollowUpScheduleResponse]


class TimelineDayEvent(BaseModel):
    event_type: str
    title: str
    details: dict


class TimelineDayGroup(BaseModel):
    date: date
    events: list[TimelineDayEvent]


class ConsultationHistoryItem(BaseModel):
    id: int
    date: datetime
    doctor_name: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    chief_complaint: Optional[str] = None
    status: str
    prescriptions: list[dict] = []
    lab_orders: list[dict] = []


class PatientMedicalHistoryResponse(BaseModel):
    patient_id: int
    patient_name: str
    medical_record: Optional[PatientMedicalRecordResponse] = None
    allergies: list[PatientAllergyResponse]
    chronic_conditions: list[PatientChronicConditionResponse]
    consultations: list[ConsultationHistoryItem]
    prescriptions: list[dict]
    lab_results: list[dict]
    vital_signs: list[PatientVitalSignsResponse]
    follow_ups: list[FollowUpScheduleResponse]
    timeline: list[TimelineDayGroup]
