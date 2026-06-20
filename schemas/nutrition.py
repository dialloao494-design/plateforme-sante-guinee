"""Nutrition / child growth monitoring schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NutritionAssessmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    weight_kg: Optional[float] = Field(None, ge=0, le=300)
    height_cm: Optional[float] = Field(None, ge=0, le=250)
    muac_cm: Optional[float] = Field(None, ge=0, le=50)
    age_months: Optional[int] = Field(None, ge=0, le=240)
    consultation_id: Optional[int] = None
    nutritional_diagnosis: Optional[str] = None
    is_follow_up: bool = False
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None


class NutritionAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    patient_id: int
    consultation_id: Optional[int] = None
    age_months: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    muac_cm: Optional[float] = None
    nutritional_status: Optional[str] = None
    nutritional_diagnosis: Optional[str] = None
    is_follow_up: bool = False
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None
    recorded_at: datetime


class NutritionDashboardStats(BaseModel):
    children_followed: int
    malnutrition_cases: int
    follow_up_visits: int
    consultations_this_month: int


class NutritionMonthlyReport(BaseModel):
    year: int
    month: int
    total_consultations: int
    malnutrition_cases: int
    follow_up_visits: int
    by_status: Dict[str, int]
