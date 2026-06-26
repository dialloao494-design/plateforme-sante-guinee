"""Laboratory HIS — patient lookup for lab staff (data from Reception registration)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class LabPatientOut(BaseModel):
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
