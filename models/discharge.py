"""Patient discharge summary and EMR archive."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class DischargeSummary(Base):
    __tablename__ = "discharge_summaries"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    visit_id = Column(Integer, ForeignKey("clinical_visits.id"), nullable=True, index=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True, index=True)
    discharge_type = Column(String(32), nullable=False, default="ambulatory")
    # ambulatory | inpatient
    status = Column(String(32), nullable=False, default="draft", index=True)
    # draft | finalized | archived
    diagnoses = Column(Text, nullable=True)
    procedures = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    clinical_summary = Column(Text, nullable=True)
    follow_up_instructions = Column(Text, nullable=True)
    invoice_validated = Column(Boolean, default=False, nullable=False)
    archived_to_emr = Column(Boolean, default=False, nullable=False)
    discharged_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    discharged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="discharge_summaries")
    patient = relationship("Patient", back_populates="discharge_summaries")
    visit = relationship("ClinicalVisit", back_populates="discharge_summaries")
    admission = relationship("Admission", back_populates="discharge_summaries")
    invoice = relationship("Invoice")
