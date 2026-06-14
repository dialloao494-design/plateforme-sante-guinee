"""Laboratory order — exam request originating from a consultation."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class LabOrder(Base):
    __tablename__ = "lab_orders"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    ordered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)

    test_code = Column(String(64), nullable=False, index=True)
    test_name = Column(String(255), nullable=False)
    priority = Column(String(16), default="routine", nullable=False)  # routine | urgent
    status = Column(String(32), default="ordered", nullable=False, index=True)
    # ordered | sample_collected | in_analysis | completed | cancelled
    clinical_notes = Column(Text, nullable=True)

    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    consultation = relationship("ClinicalConsultation", back_populates="lab_orders")
    patient = relationship("Patient")
    doctor = relationship("Doctor")
    results = relationship("LabResult", back_populates="lab_order", cascade="all, delete-orphan")
