"""Auditable clinic opening/closing handoff."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from database import Base


class ClinicOperationalShift(Base):
    __tablename__ = "clinic_operational_shifts"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="open", index=True)
    opened_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    opening_snapshot_json = Column(Text, nullable=False)
    opening_notes = Column(Text, nullable=True)
    closed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    closed_at = Column(DateTime, nullable=True)
    closing_snapshot_json = Column(Text, nullable=True)
    closing_notes = Column(Text, nullable=True)
    unresolved_acknowledged = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

