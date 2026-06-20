"""Pydantic schemas for the modular clinical information system."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Clinic ---


class ClinicCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ClinicResponse(BaseModel):
    id: int
    name: str
    address: Optional[str]
    city: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class StaffCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    role: str
    clinic_id: int


class StaffResponse(BaseModel):
    id: int
    email: str
    role: str
    clinic_id: Optional[int]
    is_active: bool = True

    class Config:
        from_attributes = True


class StaffRoleUpdate(BaseModel):
    role: str
    clinic_id: int


# --- Patient (reception intake) ---


class PatientIntakeCreate(BaseModel):
    first_name: str
    last_name: str
    age: int = Field(..., ge=0, le=130)
    gender: str = "other"
    phone: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    emergency_contact: Optional[str] = None


class PatientIntakeResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    age: int
    gender: str
    phone: Optional[str]
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

    class Config:
        from_attributes = True


class PatientSearchResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: Optional[str] = None
    age: int

    class Config:
        from_attributes = True


# --- Appointment ---


class ClinicalAppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: datetime
    duration_minutes: int = 30
    consultation_type: str = "physical"


class ClinicalAppointmentResponse(BaseModel):
    id: int
    clinic_id: Optional[int]
    patient_id: int
    doctor_id: int
    date: datetime
    duration_minutes: int
    status: str
    clinical_status: str
    consultation_type: str
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Consultation ---


class ConsultationStart(BaseModel):
    appointment_id: int
    chief_complaint: Optional[str] = None


class ConsultationUpdate(BaseModel):
    chief_complaint: Optional[str] = None
    history: Optional[str] = None
    examination: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    status: Optional[str] = None


class ConsultationResponse(BaseModel):
    id: int
    clinic_id: int
    appointment_id: int
    patient_id: int
    doctor_id: int
    status: str
    chief_complaint: Optional[str]
    history: Optional[str]
    examination: Optional[str]
    diagnosis: Optional[str]
    treatment_plan: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Lab ---


class LabOrderCreate(BaseModel):
    test_code: str
    test_name: str
    priority: str = "routine"
    clinical_notes: Optional[str] = None


class LabOrderResponse(BaseModel):
    id: int
    clinic_id: int
    consultation_id: int
    patient_id: int
    test_code: str
    test_name: str
    priority: str
    status: str
    patient_name: Optional[str] = None

    class Config:
        from_attributes = True


class LabOrderStatusUpdate(BaseModel):
    status: str


class LabResultCreate(BaseModel):
    result_summary: str
    result_data: Optional[str] = None
    reference_range: Optional[str] = None
    interpretation: Optional[str] = None


class LabResultResponse(BaseModel):
    id: int
    lab_order_id: int
    result_summary: str
    reference_range: Optional[str]
    interpretation: Optional[str]
    status: str

    class Config:
        from_attributes = True


# --- Prescription ---


class PrescriptionItemCreate(BaseModel):
    medication_name: str
    dosage: str
    route: str = "oral"
    frequency: str
    duration_days: Optional[int] = None
    quantity: Optional[int] = None
    instructions: Optional[str] = None


class PrescriptionCreate(BaseModel):
    items: list[PrescriptionItemCreate]
    notes: Optional[str] = None


class PrescriptionResponse(BaseModel):
    id: int
    clinic_id: int
    consultation_id: int
    patient_id: int
    status: str
    items: list[PrescriptionItemCreate] = []
    patient_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Pharmacy ---


class PrescriptionItemBrief(BaseModel):
    medication_name: str
    dosage: str
    frequency: str
    quantity: Optional[int] = None
    duration_days: Optional[int] = None
    instructions: Optional[str] = None


class PharmacyOrderResponse(BaseModel):
    id: int
    clinic_id: int
    prescription_id: int
    patient_id: int
    status: str
    patient_name: Optional[str] = None
    medications: Optional[str] = None
    doctor_name: Optional[str] = None
    created_at: Optional[datetime] = None
    dispensed_at: Optional[datetime] = None
    prepared_by: Optional[str] = None
    notes: Optional[str] = None
    items: list[PrescriptionItemBrief] = []

    class Config:
        from_attributes = True


class PharmacyStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


# --- Audit ---


class ClinicalAuditLogResponse(BaseModel):
    id: int
    actor_id: int
    actor_role: str
    patient_id: Optional[int]
    clinic_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[int]
    timestamp: datetime
    ip: Optional[str]

    class Config:
        from_attributes = True


# --- Billing ---


class ClinicChargeResponse(BaseModel):
    id: int
    clinic_id: int
    patient_id: int
    charge_type: str
    source_type: str
    source_id: int
    description: str
    amount_gnf: int
    payment_status: str
    payment_method: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    patient_name: Optional[str] = None

    class Config:
        from_attributes = True


class ChargePaymentRequest(BaseModel):
    payment_method: str = Field(..., pattern="^(cash|orange_money|mtn|card)$")


class DailyRevenueSummary(BaseModel):
    date: str
    total_collected_gnf: int
    total_pending_gnf: int
    paid_count: int
    pending_count: int
    by_charge_type: dict[str, int]
    by_payment_method: dict[str, int]


class ClinicOperationsSummary(BaseModel):
    clinic_id: int
    clinic_name: str
    reception_scheduled: int
    reception_waiting: int
    cashier_pending_charges: int
    cashier_pending_gnf: int
    doctor_waiting: int
    doctor_in_consultation: int
    lab_active_orders: int
    pharmacy_active_orders: int
    revenue_collected_gnf: int
    revenue_pending_gnf: int
    revenue_paid_count: int
    staff_count: int
