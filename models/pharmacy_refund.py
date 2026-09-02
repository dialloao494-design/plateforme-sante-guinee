"""Audited refunds for pharmacy charge payments."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class PharmacyRefund(Base):
    __tablename__ = "pharmacy_refunds"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    charge_id = Column(Integer, ForeignKey("clinic_charges.id"), nullable=False, index=True)
    pharmacy_order_id = Column(Integer, ForeignKey("pharmacy_orders.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    refund_number = Column(String(32), nullable=False, unique=True, index=True)
    amount_gnf = Column(Integer, nullable=False)
    refund_method = Column(String(32), nullable=False)
    reason = Column(String(64), nullable=False)
    reason_notes = Column(Text, nullable=False)
    recipient_name = Column(String(255), nullable=False)
    recipient_phone = Column(String(32), nullable=False)
    items_json = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="paid", index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient")
    charge = relationship("ClinicCharge")
    pharmacy_order = relationship("PharmacyOrder")

