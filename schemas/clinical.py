"""Pydantic schemas for the modular clinical information system."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Clinic ---


class ClinicCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    model_config = ConfigDict(from_attributes=True)


class StaffCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(..., min_length=8)
    role: str
    clinic_id: int
    first_name: Optional[str] = Field(None, max_length=128)
    last_name: Optional[str] = Field(None, max_length=128)


class StaffResponse(BaseModel):
    id: int
    email: str
    role: str
    clinic_id: Optional[int]
    is_active: bool = True
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    last_login_at: Optional[datetime] = None
    must_change_password: bool = False
    invitation_status: Optional[str] = None
    invitation_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    mfa_enabled: bool = False
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    active_sessions: int = 0
    last_password_reset_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StaffRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    clinic_id: int
    reason: str = Field(..., min_length=3, max_length=500)


class StaffProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clinic_id: int
    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)
    role: str
    reason: str = Field(..., min_length=3, max_length=500)


class StaffPasswordReset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clinic_id: int
    new_password: str = Field(..., min_length=8)


class StaffInvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    role: str
    clinic_id: int
    first_name: str = Field(..., min_length=1, max_length=128)
    last_name: str = Field(..., min_length=1, max_length=128)


class StaffInvitationResponse(BaseModel):
    staff: StaffResponse
    delivery_status: str
    expires_at: datetime


class ClinicShiftOpenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    printer_ready: bool
    offline_ready: bool
    offline_pending_count: int = Field(0, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class ClinicShiftCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    printer_ready: bool
    offline_pending_count: int = Field(0, ge=0)
    acknowledge_unresolved: bool = False
    notes: Optional[str] = Field(None, max_length=4000)


class ClinicShiftResponse(BaseModel):
    id: int
    clinic_id: int
    status: str
    opened_by_user_id: int
    opened_at: datetime
    opening_snapshot: dict
    opening_notes: Optional[str] = None
    closed_by_user_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    closing_snapshot: Optional[dict] = None
    closing_notes: Optional[str] = None
    unresolved_acknowledged: bool = False


class ClinicOnboardingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=128)
    phone: Optional[str] = Field(None, max_length=32)
    email: Optional[str] = Field(None, max_length=255)
    enabled_modules: Optional[list[str]] = None
    payment_methods: Optional[list[str]] = None
    receipt_format: Optional[str] = None
    printing_tested: Optional[bool] = None
    offline_workstation_tested: Optional[bool] = None
    test_journey_completed: Optional[bool] = None
    current_step: Optional[str] = None


class ClinicReadinessItem(BaseModel):
    key: str
    label: str
    complete: bool
    blocking: bool
    detail: str
    target: str


class ClinicOnboardingResponse(BaseModel):
    clinic_id: int
    clinic_name: str
    identity: dict
    configuration: dict
    checklist: list[ClinicReadinessItem]
    completed_count: int
    total_count: int
    percent: int
    is_operational: bool
    current_step: str
    completed_at: Optional[datetime] = None


# --- Patient (reception intake) ---


class PatientIntakeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str
    age: int = Field(..., ge=0, le=130)
    gender: str = "other"
    phone: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    emergency_contact: Optional[str] = None
    mother_name: Optional[str] = Field(None, max_length=255)
    profession: Optional[str] = None
    quartier: Optional[str] = None
    visit_destination: Optional[str] = Field(None, max_length=255)


class PatientIntakeResponse(BaseModel):
    id: int
    patient_number: Optional[str] = None
    first_name: str
    last_name: str
    age: int
    gender: str
    phone: Optional[str]
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    mother_name: Optional[str] = None
    profession: Optional[str] = None
    quartier: Optional[str] = None
    visit_destination: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PatientSearchResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: Optional[str] = None
    age: int
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    profession: Optional[str] = None
    quartier: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Appointment ---


class ClinicalAppointmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    model_config = ConfigDict(from_attributes=True)


# --- Consultation ---


class ConsultationStart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    appointment_id: int
    chief_complaint: Optional[str] = None


class ConsultationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chief_complaint: Optional[str] = None
    history: Optional[str] = None
    examination: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment_plan: Optional[str] = None
    medical_history: Optional[str] = None
    surgical_history: Optional[str] = None
    gyneco_history: Optional[str] = None
    allergies: Optional[str] = None
    current_treatments: Optional[str] = None
    observations: Optional[str] = None
    target_specialty_code: Optional[str] = None
    target_specialty_other: Optional[str] = None
    hospitalized_vitals: Optional[str] = None
    post_op_report: Optional[str] = None
    discharge_summary_text: Optional[str] = None
    discharge_authorization: Optional[str] = None
    discharge_against_advice: Optional[str] = None
    prescription_text: Optional[str] = None
    discharge_form_json: Optional[str] = None
    status: Optional[str] = None


class DoctorConsultationOpen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    chief_complaint: Optional[str] = None


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
    medical_history: Optional[str] = None
    surgical_history: Optional[str] = None
    gyneco_history: Optional[str] = None
    allergies: Optional[str] = None
    current_treatments: Optional[str] = None
    observations: Optional[str] = None
    target_specialty_code: Optional[str] = None
    target_specialty_other: Optional[str] = None
    hospitalized_vitals: Optional[str] = None
    post_op_report: Optional[str] = None
    discharge_summary_text: Optional[str] = None
    discharge_authorization: Optional[str] = None
    discharge_against_advice: Optional[str] = None
    prescription_text: Optional[str] = None
    discharge_form_json: Optional[str] = None
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Lab ---


class LabOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    patient_first_name: Optional[str] = None
    patient_last_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    patient_profession: Optional[str] = None
    patient_quartier: Optional[str] = None
    patient_phone: Optional[str] = None
    price_gnf: Optional[int] = None
    payment_status: Optional[str] = None
    result_status: Optional[str] = None
    validated_at: Optional[datetime] = None
    technician_name: Optional[str] = None
    clinical_notes: Optional[str] = None
    latest_result_id: Optional[int] = None
    result_summary: Optional[str] = None
    result_data: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LabOrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = None
    clinical_notes: Optional[str] = None


class WalkInLabTestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_code: str
    test_name: str
    price_gnf: Optional[int] = None


class LabCatalogPriceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    price_gnf: Optional[int] = None


class LabCatalogPricesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LabCatalogPriceItem] = Field(..., min_length=1)


class WalkInLabRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_id: int
    tests: list[WalkInLabTestItem] = Field(..., min_length=1)
    priority: str = "routine"
    clinical_notes: Optional[str] = None
    payment_status: str = "pending"


class DoctorMedicineDeliveryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    patient_name: str = Field(..., min_length=1, max_length=255)
    patient_id: Optional[int] = None
    medicine_name: str = Field(..., min_length=1, max_length=255)
    quantity: int = Field(..., ge=1)
    doctor_name: str = Field(..., min_length=1, max_length=255)
    reason: Optional[str] = None
    delivered_at: Optional[datetime] = None


class DoctorMedicineDeliveryResponse(BaseModel):
    id: int
    clinic_id: int
    patient_id: Optional[int] = None
    patient_name: str
    medicine_name: str
    quantity: int
    doctor_name: str
    reason: Optional[str] = None
    source: str
    delivered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabResultCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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

    model_config = ConfigDict(from_attributes=True)


# --- Prescription ---


class PrescriptionItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medication_name: str
    dosage: str
    route: str = "oral"
    frequency: str
    duration_days: Optional[int] = None
    quantity: Optional[int] = None
    instructions: Optional[str] = None


class PrescriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    doctor_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class PharmacyStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    user_agent: Optional[str] = None
    reason: Optional[str] = None
    before_json: Optional[str] = None
    after_json: Optional[str] = None
    actor_email: Optional[str] = None
    clinic_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StaffLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=500)


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

    model_config = ConfigDict(from_attributes=True)


class ChargePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
