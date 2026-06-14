"""Clinical consultation — encounter linked to an appointment."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class ClinicalConsultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=False, unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)

    status = Column(String(32), default="scheduled", nullable=False, index=True)
    # scheduled | in_progress | completed | cancelled

    chief_complaint = Column(Text, nullable=True)
    history = Column(Text, nullable=True)
    examination = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    treatment_plan = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="consultations")
    appointment = relationship("RendezVous", back_populates="clinical_consultation", uselist=False)
    patient = relationship("Patient")
    doctor = relationship("Doctor")
    lab_orders = relationship("LabOrder", back_populates="consultation", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="consultation", cascade="all, delete-orphan")
    vital_signs = relationship("PatientVitalSigns", back_populates="consultation")
    follow_ups = relationship("FollowUpSchedule", back_populates="consultation")
    admissions = relationship("Admission", back_populates="consultation")
