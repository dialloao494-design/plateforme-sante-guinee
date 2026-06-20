"""Nursing care procedures — injections, perfusions, dressings, sutures."""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class NursingProcedure(Base):
    __tablename__ = "nursing_procedures"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    procedure_type = Column(String(32), nullable=False, index=True)
    # injection | perfusion | dressing | suture | other
    procedure_date = Column(Date, nullable=False, index=True)
    nurse_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nurse_name = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="nursing_procedures")
