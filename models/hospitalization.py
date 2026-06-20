"""Admission, hospital rooms, beds, and patient stays."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class HospitalRoom(Base):
    __tablename__ = "hospital_rooms"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    ward_name = Column(String(128), nullable=False, index=True)
    room_number = Column(String(32), nullable=False)
    room_type = Column(String(64), nullable=False, default="general")
    # general | private | icu | maternity | pediatric
    capacity = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active", index=True)
    # active | maintenance | closed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="hospital_rooms")
    beds = relationship("HospitalBed", back_populates="room", cascade="all, delete-orphan")


class HospitalBed(Base):
    __tablename__ = "hospital_beds"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("hospital_rooms.id"), nullable=False, index=True)
    bed_number = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="available", index=True)
    # available | occupied | maintenance | reserved
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    room = relationship("HospitalRoom", back_populates="beds")
    stays = relationship("PatientStay", back_populates="bed")


class Admission(Base):
    __tablename__ = "admissions"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    admission_number = Column(String(32), nullable=False, unique=True, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    # pending | admitted | in_care | transferred | discharged | cancelled
    reason = Column(Text, nullable=True)
    diagnosis_summary = Column(Text, nullable=True)
    outcome = Column(String(64), nullable=True)
    # cured | improved | unchanged | transferred | deceased | left_against_advice
    notes = Column(Text, nullable=True)
    admitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    attending_clinician_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    admitted_at = Column(DateTime, nullable=True)
    discharged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="admissions")
    patient = relationship("Patient", back_populates="admissions")
    consultation = relationship("ClinicalConsultation", back_populates="admissions")
    stays = relationship("PatientStay", back_populates="admission", cascade="all, delete-orphan")
    discharge_summaries = relationship("DischargeSummary", back_populates="admission")


class PatientStay(Base):
    """Bed assignment history for an admission — supports transfers."""

    __tablename__ = "patient_stays"

    id = Column(Integer, primary_key=True, index=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=False, index=True)
    bed_id = Column(Integer, ForeignKey("hospital_beds.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    released_at = Column(DateTime, nullable=True)
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    transfer_reason = Column(Text, nullable=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    admission = relationship("Admission", back_populates="stays")
    bed = relationship("HospitalBed", back_populates="stays")
