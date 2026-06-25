"""In-clinic refund requests linked to invoices."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class ClinicRefund(Base):
    __tablename__ = "clinic_refunds"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    refund_number = Column(String(32), nullable=False, unique=True, index=True)
    original_amount_paid_gnf = Column(Integer, nullable=False, default=0)
    service_paid_for = Column(Text, nullable=True)
    amount_consumed_gnf = Column(Integer, nullable=False, default=0)
    refund_amount_gnf = Column(Integer, nullable=False, default=0)
    reason = Column(String(32), nullable=False, index=True)
    # deceased | service_cancelled | overpayment | other
    reason_notes = Column(Text, nullable=True)
    recipient_name = Column(String(255), nullable=True)
    recipient_relationship = Column(String(128), nullable=True)
    recipient_phone = Column(String(32), nullable=True)
    refund_method = Column(String(32), nullable=True)
    # cash | orange_money | bank_transfer | card | insurance_adjustment
    status = Column(String(32), nullable=False, default="pending", index=True)
    # pending | approved | paid | rejected
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    clinic = relationship("Clinic", back_populates="clinic_refunds")
    patient = relationship("Patient", back_populates="clinic_refunds")
    invoice = relationship("Invoice", back_populates="refunds")
