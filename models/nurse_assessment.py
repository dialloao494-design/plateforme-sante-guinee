"""Nurse triage / assessment — shared form for all nurses at a clinic."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class NurseAssessment(Base):
    __tablename__ = "nurse_assessments"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)

    nurse_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nurse_name = Column(String(128), nullable=True)

    temperature_c = Column(Float, nullable=True)
    bp_systolic = Column(Integer, nullable=True)
    bp_diastolic = Column(Integer, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    oxygen_saturation = Column(Integer, nullable=True)
    pain_score = Column(Integer, nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    arm_circumference_cm = Column(Float, nullable=True)
    head_circumference_cm = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    consciousness_level = Column(String(32), nullable=True)
    escalation_level = Column(String(32), nullable=True)
    vitals_observations = Column(Text, nullable=True)

    reason_for_consultation = Column(Text, nullable=True)
    history_of_present_illness = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)
    surgical_history = Column(Text, nullable=True)
    gynecological_history = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    current_treatments = Column(Text, nullable=True)
    hospitalized_daily_vitals = Column(Text, nullable=True)
    prescription = Column(Text, nullable=True)
    nurse_notes = Column(Text, nullable=True)
    care_plan = Column(Text, nullable=True)
    handover_sbar = Column(Text, nullable=True)
    medication_administration = Column(Text, nullable=True)
    specimen_collection = Column(Text, nullable=True)
    wound_assessment = Column(Text, nullable=True)
    safety_checklist = Column(Text, nullable=True)

    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="nurse_assessments")
    admission = relationship("Admission")
    consultation = relationship("ClinicalConsultation")
