"""Clinic — tenant anchor for the modular clinical information system."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Clinic(Base):
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=True)
    city = Column(String(128), nullable=True, index=True)
    phone = Column(String(32), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    staff = relationship("ClinicStaff", back_populates="clinic", cascade="all, delete-orphan")
    doctors = relationship("Doctor", back_populates="clinic")
    appointments = relationship("RendezVous", back_populates="clinic")
    consultations = relationship("ClinicalConsultation", back_populates="clinic")
    hospital_rooms = relationship("HospitalRoom", back_populates="clinic")
    admissions = relationship("Admission", back_populates="clinic")
    clinical_visits = relationship("ClinicalVisit", back_populates="clinic")
    invoices = relationship("Invoice", back_populates="clinic")
    discharge_summaries = relationship("DischargeSummary", back_populates="clinic")
    imaging_orders = relationship("ImagingOrder", back_populates="clinic")
    pharmacy_inventory = relationship("PharmacyInventoryItem", back_populates="clinic")
    patients = relationship("Patient", back_populates="clinic")


class ClinicStaff(Base):
    """Staff membership — links platform users to a clinic."""

    __tablename__ = "clinic_staff"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="staff", foreign_keys=[clinic_id])
