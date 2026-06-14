"""Schemas for clinical reporting."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class RevenueSummaryResponse(BaseModel):
    charges_collected_gnf: int
    invoices_paid_gnf: int
    total_collected_gnf: int
    pending_charges_count: int
    by_charge_type: Dict[str, int]
    paid_invoices_count: int


class ClinicalPeriodSummaryResponse(BaseModel):
    period_start: str
    period_end: str
    appointments_total: int
    appointments_completed: int
    appointments_cancelled: int
    consultations: int
    lab_orders: int
    imaging_orders: int
    pharmacy_dispensed: int
    admissions: int
    discharges: int
    revenue: RevenueSummaryResponse
