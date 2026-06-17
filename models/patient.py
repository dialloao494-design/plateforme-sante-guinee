from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("clinic_id", "user_id", name="uq_patients_clinic_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    age = Column(Integer)
    gender = Column(String)
    date_of_birth = Column(Date, nullable=True)
    phone = Column(String(32), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(255), nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    clinic = relationship("Clinic", back_populates="patients")
    user = relationship("User", back_populates="patient_profile")
    medical_record = relationship(
        "PatientMedicalRecord", back_populates="patient", uselist=False, cascade="all, delete-orphan"
    )
    allergies = relationship("PatientAllergy", back_populates="patient")
    chronic_conditions = relationship("PatientChronicCondition", back_populates="patient")
    vital_signs = relationship("PatientVitalSigns", back_populates="patient")
    follow_ups = relationship("FollowUpSchedule", back_populates="patient")
    rendezvous = relationship("RendezVous", back_populates="patient")
    clinical_notes = relationship("ClinicalNote", back_populates="patient")
    consultation_summaries = relationship("ConsultationSummary", back_populates="patient")
    documents = relationship("PatientDocument", back_populates="patient")
    admissions = relationship("Admission", back_populates="patient")
    clinical_visits = relationship("ClinicalVisit", back_populates="patient")
    visit_workflows = relationship("PatientVisitWorkflow", back_populates="patient")
    invoices = relationship("Invoice", back_populates="patient")
    discharge_summaries = relationship("DischargeSummary", back_populates="patient")
    imaging_orders = relationship("ImagingOrder", back_populates="patient")
    appointment_reminders = relationship("AppointmentReminder", back_populates="patient")
    nutrition_assessments = relationship("NutritionAssessment", back_populates="patient")
    immunization_records = relationship("ImmunizationRecord", back_populates="patient")
