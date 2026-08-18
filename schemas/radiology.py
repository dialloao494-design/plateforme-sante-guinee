"""Pydantic schemas for radiology."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ImagingOrderCreate(BaseModel):
    # Accept the full AASMA imaging catalogue (xray, ultrasound, ct_scan, mri,
    # mammography, dental_panoramic) as well as free-text "other" modalities.
    # Column is String(32); keep validation to a non-empty, bounded string.
    modality: str = Field(..., min_length=1, max_length=32)
    body_part: Optional[str] = None
    clinical_indication: Optional[str] = None
    priority: str = "routine"


class ImagingOrderStatusUpdate(BaseModel):
    status: str
    scheduled_at: Optional[datetime] = None


class ImagingReportCreate(BaseModel):
    findings: str
    impression: str
    recommendations: Optional[str] = None


class ImagingResultResponse(BaseModel):
    id: int
    order_id: int
    findings: Optional[str]
    impression: Optional[str]
    recommendations: Optional[str]
    status: str
    reported_at: Optional[datetime]
    validated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ImagingOrderResponse(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    consultation_id: int
    modality: str
    body_part: Optional[str]
    clinical_indication: Optional[str]
    priority: str
    status: str
    scheduled_at: Optional[datetime]
    patient_name: Optional[str] = None
    results: List[ImagingResultResponse] = []

    model_config = ConfigDict(from_attributes=True)
