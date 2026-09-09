"""Append-only security events for interactive authentication attempts."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from database import Base


class AuthenticationEvent(Base):
    __tablename__ = "authentication_events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(32), nullable=False, default="login")
    succeeded = Column(Boolean, nullable=False, index=True)
    reason = Column(String(64), nullable=False)
    email_fingerprint = Column(String(64), nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    request_id = Column(String(128), nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
