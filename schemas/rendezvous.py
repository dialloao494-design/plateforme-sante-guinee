from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class RendezVousBase(BaseModel):
    date: datetime = Field(..., description="Appointment start time (UTC)")
    doctor_id: int = Field(..., description="Doctor ID")
    duration_minutes: int = Field(default=30, ge=15, description="Appointment duration in minutes (minimum 15)")


class RendezVousCreate(RendezVousBase):
    """Schema for creating a new appointment"""
    pass


class RendezVousUpdate(BaseModel):
    """Schema for updating appointment status"""
    status: Optional[str] = Field(
        None, 
        description="New status (pending, confirmed, cancelled)"
    )


class RendezVousResponse(BaseModel):
    """Full appointment response with all fields"""
    id: int
    date: datetime = Field(..., description="Appointment start time")
    duration_minutes: int = Field(..., description="Duration in minutes")
    status: str = Field(..., description="Current status (pending, paid, confirmed, completed, cancelled)")
    payment_status: str = Field(..., description="Payment status (paid, unpaid)")
    is_paid: bool = Field(..., description="True when payment is confirmed")
    price: float = Field(..., description="Appointment price")
    payment_intent_id: Optional[str] = Field(None, description="Stripe payment intent ID")
    patient_id: int
    doctor_id: int
    created_at: datetime = Field(..., description="When appointment was created")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        orm_mode = True


class PatientSummary(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None

    class Config:
        orm_mode = True


class DoctorSummary(BaseModel):
    id: int
    user_id: int
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialty: Optional[str] = None
    consultation_fee: float

    class Config:
        orm_mode = True


class RendezVousWithParticipants(RendezVousResponse):
    patient: PatientSummary
    doctor: DoctorSummary

    class Config:
        orm_mode = True


class PaymentResponse(BaseModel):
    id: int
    date: datetime = Field(..., description="Appointment start time")
    price: float = Field(..., description="Appointment price")
    payment_status: str = Field(..., description="Payment status (paid, unpaid)")
    payment_intent_id: Optional[str] = Field(None, description="Stripe payment intent ID")
    patient: PatientSummary
    doctor: DoctorSummary
    status: str = Field(..., description="Appointment status")
    created_at: datetime = Field(..., description="When appointment was created")
    updated_at: datetime = Field(..., description="Last update time")

    class Config:
        orm_mode = True


class RendezVousDetailedResponse(RendezVousResponse):
    """Extended response with calculated fields and related data"""
    
    @property
    def end_time(self) -> datetime:
        """Calculate end time based on start + duration"""
        from datetime import timedelta
        return self.date + timedelta(minutes=self.duration_minutes)
    
    @property
    def duration_display(self) -> str:
        """Human-readable duration"""
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        
        if hours == 0:
            return f"{minutes} min"
        elif minutes == 0:
            return f"{hours} h"
        else:
            return f"{hours} h {minutes} min"


class PaymentConfirmation(BaseModel):
    """Schema for confirming payment and updating appointment status"""
    appointment_id: int = Field(..., description="Appointment ID")
    payment_method: Optional[str] = Field(None, description="Payment method used (optional)")
    transaction_id: Optional[str] = Field(None, description="External transaction ID (optional)")


class PaymentIntentCreate(BaseModel):
    """Request to create a Stripe payment intent."""
    appointment_id: int = Field(..., description="Appointment ID to generate payment for")


class PaymentIntentResponse(BaseModel):
    """Response containing Stripe payment intent details"""
    client_secret: str = Field(..., description="Stripe client secret for frontend")
    payment_intent_id: str = Field(..., description="Stripe payment intent ID")
    amount: int = Field(..., description="Amount in cents")
    currency: str = Field(..., description="Currency code (e.g., 'gnf')")
    status: str = Field(..., description="Payment intent status")


class PaymentIntentStatusResponse(BaseModel):
    """Response for payment intent status check"""
    payment_intent_id: str = Field(..., description="Stripe payment intent ID")
    status: str = Field(..., description="Payment status")
    amount: int = Field(..., description="Amount in cents")
    currency: str = Field(..., description="Currency code")


class CheckoutSessionResponse(BaseModel):
    """Response containing Stripe Checkout session data."""
    checkout_url: str = Field(..., description="Hosted Stripe Checkout URL")
    session_id: str = Field(..., description="Stripe Checkout session ID")
    status: Optional[str] = Field(None, description="Checkout session status")


class CheckoutSessionConfirmRequest(BaseModel):
    """Request to validate and confirm a Stripe Checkout payment."""
    session_id: str = Field(..., description="Stripe Checkout session ID")
