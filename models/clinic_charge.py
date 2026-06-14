"""In-clinic billing charges — consultation, laboratory, pharmacy."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class ClinicCharge(Base):
    __tablename__ = "clinic_charges"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)

    charge_type = Column(String(32), nullable=False, index=True)
    # consultation | laboratory | pharmacy
    source_type = Column(String(32), nullable=False)
    # appointment | lab_order | pharmacy_order
    source_id = Column(Integer, nullable=False, index=True)

    description = Column(Text, nullable=False)
    amount_gnf = Column(Integer, nullable=False, default=0)

    payment_status = Column(String(32), default="pending", nullable=False, index=True)
    # pending | paid | cancelled
    payment_method = Column(String(32), nullable=True)
    # cash | orange_money | mtn | card

    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    patient = relationship("Patient")
    clinic = relationship("Clinic")
