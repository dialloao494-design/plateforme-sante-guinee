"""Permanent patient medical record, vitals, allergies, chronic conditions, follow-ups."""

from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class PatientMedicalRecord(Base):
    """One permanent dossier per patient — never deleted."""

    __tablename__ = "patient_medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, unique=True, index=True)
    blood_type = Column(String(8), nullable=True)
    general_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="medical_record")


class PatientAllergy(Base):
    __tablename__ = "patient_allergies"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    allergen = Column(String(255), nullable=False)
    severity = Column(String(32), default="moderate", nullable=False)  # mild | moderate | severe
    reaction = Column(Text, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="allergies")


class PatientChronicCondition(Base):
    __tablename__ = "patient_chronic_conditions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    condition_name = Column(String(255), nullable=False)
    diagnosed_at = Column(Date, nullable=True)
    status = Column(String(32), default="active", nullable=False)  # active | resolved
    notes = Column(Text, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="chronic_conditions")


class PatientVitalSigns(Base):
    __tablename__ = "patient_vital_signs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    bp_systolic = Column(Integer, nullable=True)
    bp_diastolic = Column(Integer, nullable=True)
    heart_rate = Column(Integer, nullable=True)
    temperature_c = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    bmi = Column(Float, nullable=True)
    spo2 = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="vital_signs")
    consultation = relationship("ClinicalConsultation", back_populates="vital_signs")


class FollowUpSchedule(Base):
    __tablename__ = "follow_up_schedules"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False, index=True)
    interval_type = Column(String(16), nullable=False)  # 7d | 15d | 1m | 3m | 6m | custom
    visit_type = Column(String(32), default="follow_up", nullable=False)  # consultation | follow_up
    reason = Column(Text, nullable=True)
    clinical_notes = Column(Text, nullable=True)
    status = Column(String(32), default="scheduled", nullable=False, index=True)
    # scheduled | completed | overdue | cancelled
    follow_up_appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="follow_ups")
    doctor = relationship("Doctor")
    consultation = relationship("ClinicalConsultation", back_populates="follow_ups")
