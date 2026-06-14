"""Pharmacy order — dispensing workflow for a prescription."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class PharmacyOrder(Base):
    __tablename__ = "pharmacy_orders"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    status = Column(String(32), default="pending", nullable=False, index=True)
    # pending | preparing | ready | dispensed | cancelled
    prepared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    dispensed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    prescription = relationship("Prescription", back_populates="pharmacy_orders")
    patient = relationship("Patient")
