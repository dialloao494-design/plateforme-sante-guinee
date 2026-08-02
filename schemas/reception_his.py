"""Pydantic schemas for Reception HIS workflow."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class EmergencyContactPayload(BaseModel):
    same_address_as_patient: bool = False
    full_name: str = Field(..., min_length=1, max_length=255)
    relationship: Optional[str] = None
    phone: str = Field(..., min_length=1, max_length=32)
    address: Optional[str] = None
    commune: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    email: Optional[str] = None


class PayerPayload(BaseModel):
    payer_type: Literal["patient", "insurance", "company", "employee", "dg", "mshp"] = "patient"
    insurance_company: Optional[str] = None
    insurance_number: Optional[str] = None
    company_name: Optional[str] = None
    notes: Optional[str] = None


class DuplicatePatientMatch(BaseModel):
    id: int
    patient_number: Optional[str] = None
    first_name: str
    last_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    match_reasons: List[str] = []


class PatientRegistrationCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    gender: str = Field(..., min_length=1, max_length=16)
    date_of_birth: Optional[date] = None
    date_of_birth_precision: Literal["full", "year", "unknown"] = "full"
    age_years: Optional[int] = Field(None, ge=0, le=130)
    phone: str = Field(..., min_length=1, max_length=32)
    address: str = Field(..., min_length=1)
    photo_url: Optional[str] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    mother_first_name: Optional[str] = None
    mother_last_name: Optional[str] = None
    profession: Optional[str] = None
    preferred_language: Optional[str] = None
    email: Optional[str] = None
    phone_secondary: Optional[str] = None
    commune: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    emergency_contact: EmergencyContactPayload
    payer: PayerPayload = Field(default_factory=PayerPayload)
    confirm_duplicate: bool = False
    is_newborn: bool = False
    registration_date: Optional[date] = None


class PatientRegistrationResponse(BaseModel):
    id: int
    patient_number: str
    qr_token: str
    first_name: str
    last_name: str
    age: int
    gender: str
    date_of_birth: Optional[date] = None
    date_of_birth_precision: str = "full"
    phone: Optional[str] = None
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    commune: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    place_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    mother_first_name: Optional[str] = None
    mother_last_name: Optional[str] = None
    profession: Optional[str] = None
    preferred_language: Optional[str] = None
    photo_url: Optional[str] = None
    emergency_contact_json: Optional[str] = None
    payer_json: Optional[str] = None
    is_newborn: bool = False
    registration_date: Optional[date] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DuplicateCheckRequest(BaseModel):
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None


class PatientSearchResult(BaseModel):
    id: int
    patient_number: Optional[str] = None
    qr_token: Optional[str] = None
    first_name: str
    last_name: str
    phone: Optional[str] = None
    age: int
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    date_of_birth_precision: Optional[str] = None
    payer_json: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReceptionAdmissionCreate(BaseModel):
    patient_id: int
    admission_date: date
    admission_time: Optional[time] = None
    department: Optional[str] = Field(None, max_length=128)
    services: List[str] = Field(default_factory=list)
    attending_clinician_user_id: Optional[int] = None
    attending_physician_name: Optional[str] = None
    admission_type: Literal["emergency", "outpatient", "hospitalization", "specialized_consultation"]
    confirmation_status: Optional[Literal["confirmed", "pending"]] = None
    specialty_code: Optional[str] = None
    specialty_other: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _require_service(self):
        if self.services or (self.department and self.department.strip()):
            return self
        raise ValueError("Sélectionnez au moins un service")


SERVICE_REQUEST_CATEGORIES = Literal[
    "laboratory",
    "nursing",
    "imaging",
    "pharmacy",
    "doctor",
    "service",
    "surgery",
    "consultation",
    "other",
]


class ServiceRequestCreate(BaseModel):
    patient_id: int
    admission_id: Optional[int] = None
    service_category: SERVICE_REQUEST_CATEGORIES
    # When catalog_code is set, the server overwrites name/charge_type/price.
    service_name: str = Field(..., min_length=1, max_length=255)
    department: Optional[str] = Field(None, max_length=128)
    catalog_code: Optional[str] = Field(None, max_length=64)
    charge_type: Optional[str] = Field(None, max_length=64)
    unit_price_gnf: Optional[int] = Field(None, ge=0)
    # Required when client wants a non-catalog negotiated unit price.
    price_override_reason: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    status: Literal["pending", "approved", "completed", "cancelled"] = "pending"


class ServiceRequestUpdate(BaseModel):
    service_category: Optional[SERVICE_REQUEST_CATEGORIES] = None
    service_name: Optional[str] = Field(None, min_length=1, max_length=255)
    department: Optional[str] = Field(None, max_length=128)
    catalog_code: Optional[str] = Field(None, max_length=64)
    charge_type: Optional[str] = Field(None, max_length=64)
    unit_price_gnf: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    status: Optional[Literal["pending", "approved", "completed", "cancelled"]] = None


class ServiceRequestResponse(BaseModel):
    id: int
    request_number: str
    patient_id: int
    patient_name: Optional[str] = None
    patient_number: Optional[str] = None
    admission_id: Optional[int] = None
    service_category: str
    service_name: str
    department: Optional[str] = None
    catalog_code: Optional[str] = None
    charge_type: Optional[str] = None
    unit_price_gnf: Optional[int] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReceptionAdmissionResponse(BaseModel):
    id: int
    admission_number: str
    patient_id: int
    patient_name: Optional[str] = None
    department: Optional[str] = None
    services: List[str] = []
    admission_type: Optional[str] = None
    status: str
    admitted_at: Optional[datetime] = None
    attending_clinician_user_id: Optional[int] = None

    class Config:
        from_attributes = True


class ReceptionInvoiceLineItem(BaseModel):
    charge_type: str = Field(..., min_length=1, max_length=32)
    description: str = Field(..., min_length=1)
    quantity: int = Field(1, ge=1)
    unit_price_gnf: int = Field(..., ge=0)
    source_type: Optional[str] = "reception"
    # DSR number (e.g. DSR-017-000044) when billing a service request.
    source_ref: Optional[str] = None
    catalog_code: Optional[str] = Field(None, max_length=64)
    price_override_reason: Optional[str] = Field(None, max_length=255)


class ReceptionInvoiceCreate(BaseModel):
    patient_id: int
    department: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    total_amount_gnf: Optional[int] = Field(None, ge=0)
    items: Optional[List[ReceptionInvoiceLineItem]] = None
    exemption_percent: float = Field(0, ge=0, le=100)
    # Required when exemption_percent > 0.
    exemption_reason: Optional[str] = Field(None, max_length=255)
    billing_date: Optional[date] = None

    @model_validator(mode="after")
    def _require_lines_or_legacy(self):
        if self.exemption_percent and float(self.exemption_percent) > 0:
            if not (self.exemption_reason or "").strip():
                raise ValueError("exemption_reason est requis lorsque exemption_percent > 0")
        if self.items:
            return self
        if self.description and self.total_amount_gnf is not None:
            return self
        raise ValueError("Fournir items[] ou description + total_amount_gnf")


class InvoiceItemOut(BaseModel):
    id: int
    charge_type: str
    description: str
    quantity: int
    unit_price_gnf: int
    amount_gnf: int

    class Config:
        from_attributes = True


class ReceptionPaymentCreate(BaseModel):
    amount_gnf: int = Field(..., gt=0)
    payment_method: Literal["cash", "orange_money", "bank_transfer", "card", "insurance"]
    reference: Optional[str] = None


class PaymentRecordOut(BaseModel):
    id: int
    amount_gnf: int
    payment_method: str
    reference: Optional[str] = None
    paid_at: datetime

    class Config:
        from_attributes = True


class ReceptionInvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    patient_id: int
    patient_name: Optional[str] = None
    department: Optional[str] = None
    status: str
    subtotal_amount_gnf: int = 0
    exemption_percent: float = 0
    exemption_amount_gnf: int = 0
    total_amount_gnf: int
    paid_amount_gnf: int
    remaining_balance_gnf: int
    issued_at: Optional[datetime] = None
    description: Optional[str] = None
    items: List[InvoiceItemOut] = []
    payments: List[PaymentRecordOut] = []

    class Config:
        from_attributes = True


class RefundCreate(BaseModel):
    invoice_id: int
    service_paid_for: str = Field(..., min_length=1)
    amount_consumed_gnf: int = Field(..., ge=0)
    refund_amount_gnf: int = Field(..., gt=0)
    reason: Literal["deceased", "service_cancelled", "overpayment", "other"]
    reason_notes: Optional[str] = None
    recipient_name: str = Field(..., min_length=1)
    recipient_relationship: Optional[str] = None
    recipient_phone: str = Field(..., min_length=1)
    refund_method: Literal["cash", "orange_money", "bank_transfer", "card", "insurance_adjustment"]


class RefundStatusUpdate(BaseModel):
    status: Literal["approved", "rejected", "paid"]
    refund_method: Optional[str] = None


class RefundResponse(BaseModel):
    id: int
    refund_number: str
    patient_id: int
    patient_name: Optional[str] = None
    invoice_id: int
    invoice_number: Optional[str] = None
    original_amount_paid_gnf: int
    service_paid_for: Optional[str] = None
    amount_consumed_gnf: int
    refund_amount_gnf: int
    reason: str
    reason_notes: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_relationship: Optional[str] = None
    recipient_phone: Optional[str] = None
    refund_method: Optional[str] = None
    status: str
    created_at: datetime
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReceptionDashboardStats(BaseModel):
    total_patients: int
    patients_registered_today: int
    admissions_today: int
    hospitalized_patients: int
    paid_invoices: int = 0
    unpaid_invoices: int = 0
    revenue_today_gnf: int
    revenue_month_gnf: int
    refunds_total_gnf: int = 0
    outstanding_invoices: int
    gender_distribution: dict
    department_distribution: dict
    recent_registrations: List[dict] = []
    recent_admissions: List[dict] = []
    recent_payments: List[dict] = []
    recent_refunds: List[dict] = []


class ReceptionPeriodReport(BaseModel):
    period_start: str
    period_end: str
    patients_registered: int
    admissions: int
    hospitalizations: int
    invoices_paid: int
    invoices_unpaid: int
    payments_received_gnf: int
    refunds_gnf: int
    net_revenue_gnf: int
    revenue_by_service: dict
