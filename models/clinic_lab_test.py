"""Per-clinic laboratory examination catalog with editable prices."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


class ClinicLabTest(Base):
    __tablename__ = "clinic_lab_tests"
    __table_args__ = (UniqueConstraint("clinic_id", "code", name="uq_clinic_lab_tests_clinic_code"),)

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    code = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    category_label = Column(String(128), nullable=False)
    price_gnf = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic")
