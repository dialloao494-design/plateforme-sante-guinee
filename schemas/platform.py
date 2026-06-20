"""Platform owner administration schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PlatformOwnerSummary(BaseModel):
    total_clinics: int
    active_clinics: int
    total_staff: int
    total_patients: int
    monthly_consultations: int


class PlatformClinicSummary(BaseModel):
    id: int
    name: str
    city: Optional[str]
    is_active: bool
    status: str
    category: str
    created_at: datetime
    staff_count: int
    patient_count: int
    consultation_count: int
    last_activity_at: Optional[datetime]
    admin_email: Optional[str]


class PlatformRoleBreakdown(BaseModel):
    role: str
    label: str
    count: int


class PlatformModuleUsage(BaseModel):
    consultations: int = 0
    laboratory: int = 0
    pharmacy: int = 0
    pev: int = 0
    nutrition: int = 0
    nursing: int = 0
    hospitalization: int = 0


class PlatformStaffMember(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: str
    phone: Optional[str]
    is_active: bool
    last_activity_at: Optional[datetime]


class PlatformClinicDetail(BaseModel):
    id: int
    name: str
    address: Optional[str]
    city: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_active: bool
    status: str
    category: str
    created_at: datetime
    admin_email: Optional[str]
    admin_name: Optional[str]
    staff_count: int
    patient_count: int
    consultation_count: int
    monthly_consultations: int
    last_activity_at: Optional[datetime]
    role_breakdown: List[PlatformRoleBreakdown]
    module_usage: PlatformModuleUsage


class PlatformStaffPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)
