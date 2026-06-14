"""Clinical visit — groups all services for one patient encounter."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class ClinicalVisit(Base):
    __tablename__ = "clinical_visits"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="open", index=True)
    # open | billing | paid | discharged | archived
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    discharged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="clinical_visits")
    patient = relationship("Patient", back_populates="clinical_visits")
    invoices = relationship("Invoice", back_populates="visit")
    discharge_summaries = relationship("DischargeSummary", back_populates="visit")
    charges = relationship("ClinicCharge", back_populates="visit")
