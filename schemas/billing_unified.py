"""Pydantic schemas for unified billing."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InvoiceGenerateRequest(BaseModel):
    patient_id: int
    visit_id: Optional[int] = None


class InvoicePayRequest(BaseModel):
    payment_method: str = Field(..., pattern="^(cash|orange_money|mtn|card)$")


class InvoiceItemResponse(BaseModel):
    id: int
    charge_type: str
    description: str
    quantity: int
    unit_price_gnf: int
    amount_gnf: int

    model_config = ConfigDict(from_attributes=True)


class PaymentRecordResponse(BaseModel):
    id: int
    amount_gnf: int
    payment_method: str
    paid_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    visit_id: Optional[int]
    invoice_number: str
    status: str
    total_amount_gnf: int
    paid_amount_gnf: int
    issued_at: Optional[datetime]
    paid_at: Optional[datetime]
    patient_name: Optional[str] = None
    items: List[InvoiceItemResponse] = []

    model_config = ConfigDict(from_attributes=True)
