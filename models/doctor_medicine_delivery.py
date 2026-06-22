"""Medicines delivered from doctor office stock — not pharmacy inventory."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class DoctorMedicineDelivery(Base):
    __tablename__ = "doctor_medicine_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True, index=True)
    patient_name = Column(String(255), nullable=False)
    medicine_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    doctor_name = Column(String(255), nullable=False)
    reason = Column(Text, nullable=True)
    source = Column(String(32), default="doctor_office", nullable=False)
    delivered_at = Column(DateTime, nullable=False, index=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    clinic = relationship("Clinic")
    patient = relationship("Patient")
