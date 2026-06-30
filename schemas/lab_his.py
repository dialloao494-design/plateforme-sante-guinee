"""Laboratory HIS — patient lookup for lab staff (data from Reception registration)."""

from __future__ import annotations

from datetime import date, datetime
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


class LabServiceRequestOut(BaseModel):
    id: str
    exam_name: str
    payment_status: str
    requested_at: Optional[datetime] = None
    requested_by: Optional[str] = None
    lab_order_id: Optional[int] = None


class LabQueueRowOut(BaseModel):
    patient_id: int
    patient_number: Optional[str] = None
    last_name: str
    first_name: str
    exams: str
    status: str
    date_time: Optional[datetime] = None
