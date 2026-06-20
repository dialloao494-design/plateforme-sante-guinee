"""Nursing care procedure schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


PROCEDURE_TYPES = ("injection", "perfusion", "dressing", "suture", "other")


class NursingProcedureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    procedure_type: str = Field(..., pattern="^(injection|perfusion|dressing|suture|other)$")
    procedure_date: date
    procedure_time: Optional[str] = Field(None, max_length=8)
    nurse_name: Optional[str] = Field(None, max_length=128)
    notes: Optional[str] = None


class NursingProcedureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clinic_id: int
    patient_id: int
    procedure_type: str
    procedure_date: date
    procedure_time: Optional[str] = None
    nurse_user_id: Optional[int] = None
    nurse_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    patient_name: Optional[str] = None


class NursingDashboardStats(BaseModel):
    daily_procedures: int
    monthly_procedures: int
    injections: int
    perfusions: int
    dressings: int
    sutures: int
    other: int
    by_type: Dict[str, int]


class NursingMonthlyReport(BaseModel):
    year: int
    month: int
    clinic_id: Optional[int] = None
    total_procedures: int
    by_type: Dict[str, int]
    daily_tally: List[Dict[str, int]]
    register_rows: List[dict] = Field(default_factory=list)
