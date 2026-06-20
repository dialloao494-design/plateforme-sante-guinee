"""Shared schemas for paper-register views."""

from __future__ import annotations

from datetime import date
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ClinicalPatientSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    age_display: Optional[str] = None
    mother_or_guardian: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


class ClinicalRegisterRow(BaseModel, Generic[T]):
    line_number: int
    record: T
    patient: ClinicalPatientSnapshot
