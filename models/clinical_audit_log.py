"""Immutable audit trail for patient dossier reads and writes."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


class ClinicalAuditLog(Base):
    __tablename__ = "clinical_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    actor_role = Column(String(32), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    action = Column(String(32), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip = Column(String(64), nullable=True)
