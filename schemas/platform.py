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
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    mfa_enabled: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    invitation_status: Optional[str] = None
    invitation_expires_at: Optional[datetime] = None
    active_sessions: int = 0
    last_password_reset_at: Optional[datetime] = None


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
    suspended_at: Optional[datetime] = None
    suspension_reason: Optional[str] = None
    archived_at: Optional[datetime] = None
    configuration: Dict = Field(default_factory=dict)


class PlatformStaffPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=8)


class PlatformLifecycleRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class PlatformAccount(BaseModel):
    id: int
    email: str
    role: str
    clinic_id: Optional[int] = None
    clinic_name: Optional[str] = None
    category: str
    classification_reasons: List[str] = Field(default_factory=list)
    is_active: bool
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    mfa_enabled: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    active_sessions: int = 0
    can_delete: bool = False


class PlatformClinicConfigurationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    address: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    email: Optional[str] = Field(None, max_length=255)
    enabled_modules: Optional[List[str]] = None
    payment_methods: Optional[List[str]] = None
    receipt_template: Optional[str] = Field(None, max_length=64)
    catalogue_version: Optional[str] = Field(None, max_length=64)
    offline_workstations_enabled: Optional[bool] = None
    data_retention_days: Optional[int] = Field(None, ge=30, le=3650)
    mfa_policy: Optional[str] = Field(None, pattern="^(optional|administrators|all_staff)$")
    trusted_workstation_days: Optional[int] = Field(None, ge=0, le=90)


class PlatformSession(BaseModel):
    id: int
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    current: bool = False


class PlatformClinicStateRequest(BaseModel):
    action: str = Field(..., pattern="^(suspend|reactivate|archive)$")
    reason: str = Field(..., min_length=5, max_length=500)
    confirmation: str = Field(..., min_length=2, max_length=255)


class PlatformDataResetRequest(BaseModel):
    confirmation: str = Field(..., min_length=2, max_length=255)
    reason: str = Field(..., min_length=5, max_length=500)
    acknowledge_irreversible: bool
    waive_backup: bool = False


class PlatformPatientMergeRequest(BaseModel):
    source_patient_id: int
    target_patient_id: int
    confirmation: str = Field(..., min_length=2, max_length=64)
    reason: str = Field(..., min_length=5, max_length=500)
    execute: bool = False
