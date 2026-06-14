"""Prescription — medication order from a consultation."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    prescriber_doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)

    status = Column(String(32), default="active", nullable=False, index=True)
    # active | partially_dispensed | dispensed | cancelled
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    consultation = relationship("ClinicalConsultation", back_populates="prescriptions")
    patient = relationship("Patient")
    prescriber = relationship("Doctor")
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")
    pharmacy_orders = relationship("PharmacyOrder", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)

    medication_name = Column(String(255), nullable=False)
    dosage = Column(String(128), nullable=False)
    route = Column(String(64), default="oral", nullable=False)
    frequency = Column(String(128), nullable=False)
    duration_days = Column(Integer, nullable=True)
    quantity = Column(Integer, nullable=True)
    instructions = Column(Text, nullable=True)

    prescription = relationship("Prescription", back_populates="items")
