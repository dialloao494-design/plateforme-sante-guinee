"""PEV / immunization records and national vaccine schedule."""

from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class VaccineScheduleItem(Base):
    """National PEV schedule template (age-based due vaccines)."""

    __tablename__ = "vaccine_schedule_items"

    id = Column(Integer, primary_key=True, index=True)
    vaccine_code = Column(String(32), nullable=False, index=True)
    vaccine_name = Column(String(128), nullable=False)
    dose_label = Column(String(64), nullable=False)  # e.g. "Dose 1", "Rappel"
    age_months = Column(Integer, nullable=False)  # due at this age (months from birth)
    grace_days = Column(Integer, default=14, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class ImmunizationRecord(Base):
    """Administered vaccination for a patient."""

    __tablename__ = "immunization_records"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    vaccine_code = Column(String(32), nullable=False, index=True)
    vaccine_name = Column(String(128), nullable=False)
    dose_label = Column(String(64), nullable=True)
    batch_number = Column(String(64), nullable=True)
    administered_at = Column(Date, nullable=False)
    administered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="immunization_records")
