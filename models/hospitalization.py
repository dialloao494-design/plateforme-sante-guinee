"""Admission, hospital rooms, beds, and patient stays."""

from datetime import datetime
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship

from database import Base


class HospitalWard(Base):
    """A clinic-owned care area. Pricing deliberately does not live here."""

    __tablename__ = "hospital_wards"
    __table_args__ = (
        UniqueConstraint("clinic_id", "code", name="uq_hospital_wards_clinic_code"),
        UniqueConstraint("clinic_id", "name", name="uq_hospital_wards_clinic_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    code = Column(String(32), nullable=False)
    name = Column(String(128), nullable=False)
    service_type = Column(String(64), nullable=False, default="general")
    status = Column(String(24), nullable=False, default="active", index=True)
    location = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    rooms = relationship("HospitalRoom", back_populates="ward")


class HospitalRoom(Base):
    __tablename__ = "hospital_rooms"
    __table_args__ = (
        UniqueConstraint("clinic_id", "ward_name", "room_number", name="uq_hospital_rooms_location"),
    )

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    ward_id = Column(Integer, ForeignKey("hospital_wards.id"), nullable=True, index=True)
    ward_name = Column(String(128), nullable=False, index=True)
    room_number = Column(String(32), nullable=False)
    room_type = Column(String(64), nullable=False, default="general")
    # general | private | icu | maternity | pediatric
    capacity = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="active", index=True)
    # active | maintenance | closed
    notes = Column(Text, nullable=True)
    isolation_capable = Column(Boolean, nullable=False, default=False)
    accessible = Column(Boolean, nullable=False, default=False)
    sex_policy = Column(String(24), nullable=False, default="mixed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="hospital_rooms")
    ward = relationship("HospitalWard", back_populates="rooms")
    beds = relationship("HospitalBed", back_populates="room", cascade="all, delete-orphan")


class HospitalBed(Base):
    __tablename__ = "hospital_beds"
    __table_args__ = (
        UniqueConstraint("room_id", "bed_number", name="uq_hospital_beds_room_number"),
        UniqueConstraint("stable_code", name="uq_hospital_beds_stable_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("hospital_rooms.id"), nullable=False, index=True)
    bed_number = Column(String(32), nullable=False)
    stable_code = Column(String(64), nullable=False, index=True, default=lambda: f"BED-{uuid.uuid4().hex[:16].upper()}")
    accommodation_type = Column(String(24), nullable=False, default="regular_bed")
    pediatric_suitable = Column(Boolean, nullable=False, default=False)
    newborn_suitable = Column(Boolean, nullable=False, default=False)
    isolation_suitable = Column(Boolean, nullable=False, default=False)
    accessible = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="available", index=True)
    # available | reserved | occupied | cleaning | maintenance | unavailable
    status_reason = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    reserved_for_admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True, index=True)
    reserved_until = Column(DateTime, nullable=True)
    last_cleaned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    room = relationship("HospitalRoom", back_populates="beds")
    stays = relationship("PatientStay", back_populates="bed")
    status_events = relationship("BedStatusEvent", back_populates="bed", cascade="all, delete-orphan")


class Admission(Base):
    __tablename__ = "admissions"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=True, index=True)
    admission_number = Column(String(32), nullable=False, unique=True, index=True)
    department = Column(String(128), nullable=True, index=True)
    services_json = Column(Text, nullable=True)
    admission_type = Column(String(32), nullable=True, index=True)
    # emergency | outpatient | hospitalization
    status = Column(String(32), nullable=False, default="pending", index=True)
    # pending | admitted | in_care | transferred | discharged | cancelled
    reason = Column(Text, nullable=True)
    diagnosis_summary = Column(Text, nullable=True)
    outcome = Column(String(64), nullable=True)
    # cured | improved | unchanged | transferred | deceased | left_against_advice
    notes = Column(Text, nullable=True)
    specialty_code = Column(String(64), nullable=True)
    specialty_other = Column(String(255), nullable=True)
    bed_number = Column(String(32), nullable=True)
    cabin_number = Column(String(32), nullable=True)
    admitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    attending_clinician_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    admitted_at = Column(DateTime, nullable=True)
    discharged_at = Column(DateTime, nullable=True)
    expected_discharge_at = Column(DateTime, nullable=True)
    placement_age_group = Column(String(16), nullable=False, default="adult")
    requires_isolation = Column(Boolean, nullable=False, default=False)
    requires_accessible = Column(Boolean, nullable=False, default=False)
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
    __table_args__ = (
        Index(
            "uq_patient_stays_current_bed",
            "bed_id",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        Index(
            "uq_patient_stays_current_admission",
            "admission_id",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
    )

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


class BedStatusEvent(Base):
    """Immutable bed lifecycle evidence used for turnover and incident review."""

    __tablename__ = "bed_status_events"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    bed_id = Column(Integer, ForeignKey("hospital_beds.id"), nullable=False, index=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True, index=True)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False)
    reason = Column(Text, nullable=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    bed = relationship("HospitalBed", back_populates="status_events")
