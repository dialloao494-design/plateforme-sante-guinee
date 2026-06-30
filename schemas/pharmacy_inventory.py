"""Pharmacy inventory schemas."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PharmacyInventoryItemResponse(BaseModel):
    id: int
    clinic_id: int
    sku: str
    medication_name: str
    quantity: int
    reorder_level: int
    unit_price_gnf: int
    purchase_price_gnf: Optional[int] = None
    low_stock: bool = False
    out_of_stock: bool = False
    batch_number: Optional[str] = None
    expiry_date: Optional[date] = None
    supplier: Optional[str] = None

    class Config:
        from_attributes = True


class PharmacyInventoryUpsert(BaseModel):
    sku: str = Field(..., min_length=2, max_length=64)
    medication_name: str = Field(..., min_length=2, max_length=255)
    quantity: int = Field(..., ge=0)
    reorder_level: int = Field(10, ge=0)
    unit_price_gnf: int = Field(25_000, ge=0)
    purchase_price_gnf: Optional[int] = Field(None, ge=0)
    batch_number: Optional[str] = Field(None, max_length=64)
    expiry_date: Optional[date] = None
    supplier: Optional[str] = Field(None, max_length=128)


class PharmacyInventoryAdjust(BaseModel):
    delta: int


class PharmacyInventoryUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=2, max_length=64)
    medication_name: Optional[str] = Field(None, min_length=2, max_length=255)
    quantity: Optional[int] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    unit_price_gnf: Optional[int] = Field(None, ge=0)
    purchase_price_gnf: Optional[int] = Field(None, ge=0)
    batch_number: Optional[str] = Field(None, max_length=64)
    expiry_date: Optional[date] = None
    supplier: Optional[str] = Field(None, max_length=128)
