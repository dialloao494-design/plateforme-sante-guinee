"""Pharmacy inventory schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PharmacyInventoryItemResponse(BaseModel):
    id: int
    clinic_id: int
    sku: str
    medication_name: str
    quantity: int
    reorder_level: int
    unit_price_gnf: int
    low_stock: bool = False

    class Config:
        from_attributes = True


class PharmacyInventoryUpsert(BaseModel):
    sku: str = Field(..., min_length=2, max_length=64)
    medication_name: str = Field(..., min_length=2, max_length=255)
    quantity: int = Field(..., ge=0)
    reorder_level: int = Field(10, ge=0)
    unit_price_gnf: int = Field(25_000, ge=0)


class PharmacyInventoryAdjust(BaseModel):
    delta: int
