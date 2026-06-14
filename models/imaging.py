"""Radiology / imaging orders and results."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class ImagingOrder(Base):
    __tablename__ = "imaging_orders"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False, index=True)
    modality = Column(String(32), nullable=False, index=True)
    # xray | ultrasound | ct_scan | mri
    body_part = Column(String(128), nullable=True)
    clinical_indication = Column(Text, nullable=True)
    priority = Column(String(16), nullable=False, default="routine")
    status = Column(String(32), nullable=False, default="ordered", index=True)
    # ordered | scheduled | in_progress | reported | validated | cancelled
    scheduled_at = Column(DateTime, nullable=True)
    ordered_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="imaging_orders")
    patient = relationship("Patient", back_populates="imaging_orders")
    consultation = relationship("ClinicalConsultation", back_populates="imaging_orders")
    results = relationship("ImagingResult", back_populates="order", cascade="all, delete-orphan")


class ImagingResult(Base):
    __tablename__ = "imaging_results"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("imaging_orders.id"), nullable=False, index=True)
    findings = Column(Text, nullable=True)
    impression = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    attachment_url = Column(Text, nullable=True)
    reported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reported_at = Column(DateTime, nullable=True)
    validated_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default="draft", index=True)
    # draft | reported | validated
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    order = relationship("ImagingOrder", back_populates="results")
