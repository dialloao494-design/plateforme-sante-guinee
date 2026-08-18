"""Pydantic schemas for discharge."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DischargeChecklistResponse(BaseModel):
    visit_id: int
    patient_id: int
    pending_charges: int
    unpaid_invoices: int
    pending_pharmacy_orders: int
    invoice_validated: bool
    ready_for_discharge: bool


class OpenVisitResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    status: str
    consultation_id: Optional[int] = None
    started_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DischargeRequest(BaseModel):
    visit_id: int
    follow_up_instructions: Optional[str] = None
    force: bool = False


class DischargeSummaryResponse(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    visit_id: Optional[int]
    discharge_type: str
    status: str
    diagnoses: Optional[str]
    procedures: Optional[str]
    medications: Optional[str]
    clinical_summary: Optional[str]
    follow_up_instructions: Optional[str]
    invoice_validated: bool
    archived_to_emr: bool
    discharged_at: Optional[datetime]
    patient_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
