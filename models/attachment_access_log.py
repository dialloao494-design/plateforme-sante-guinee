"""Immutable audit trail for clinical attachment downloads (RGPD / secret médical)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from database import Base


class AttachmentAccessLog(Base):
    __tablename__ = "attachment_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_role = Column(String(32), nullable=False)
    client_ip = Column(String(64), nullable=True)
    storage_kind = Column(String(16), nullable=False, default="secure")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
