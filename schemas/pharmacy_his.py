"""Pharmacy HIS — patient lookup and walk-in service requests."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PharmacyPatientOut(BaseModel):
    id: int
    patient_number: Optional[str] = None
    qr_token: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: Optional[date] = None
    age: int = 0
    gender: Optional[str] = None
    profession: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    quartier: Optional[str] = None

    class Config:
        from_attributes = True


class PharmacyServiceLineItem(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., ge=1)
    unit_price_gnf: int = Field(..., ge=0)


class PharmacyServiceRequestCreate(BaseModel):
    patient_id: int
    items: list[PharmacyServiceLineItem] = Field(..., min_length=1)
    notes: Optional[str] = None


class PharmacyServiceLineOut(BaseModel):
    product_name: str
    quantity: int
    unit_price_gnf: int
    total_gnf: int


class PharmacyServiceRequestResponse(BaseModel):
    order_id: int
    charge_id: int
    patient_id: int
    subtotal_gnf: int = 0
    exemption_percent: float = 0
    exemption_amount_gnf: int = 0
    total_gnf: int
    paid_amount_gnf: int = 0
    remaining_gnf: int
    payment_status: str
    payment_method: Optional[str] = None
    items: list[PharmacyServiceLineOut]


class PharmacyChargePaymentCreate(BaseModel):
    payment_method: str = Field(..., min_length=1, max_length=32)
    amount_received_gnf: int = Field(..., ge=0)
    exemption_percent: float = Field(0, ge=0, le=100)
