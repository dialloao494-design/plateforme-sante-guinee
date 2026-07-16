"""Reception service requests — routed to lab, nursing, imaging, pharmacy, etc."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class ClinicServiceRequest(Base):
    __tablename__ = "clinic_service_requests"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    admission_id = Column(Integer, ForeignKey("admissions.id"), nullable=True, index=True)
    request_number = Column(String(32), nullable=False, unique=True, index=True)
    service_category = Column(String(32), nullable=False, index=True)
    # laboratory | nursing | imaging | pharmacy | doctor | service | other
    service_name = Column(String(255), nullable=False)
    department = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    # pending | approved | completed | cancelled
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic")
    patient = relationship("Patient")
    admission = relationship("Admission")
