"""Server-side idempotency for client retries (offline sync / network replay)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from database import Base


class ApiClientIdempotencyKey(Base):
    """Persists the first successful response for a client request id."""

    __tablename__ = "api_client_idempotency_keys"
    __table_args__ = (
        UniqueConstraint("client_request_id", name="uq_api_client_idempotency_request_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    client_request_id = Column(String(128), nullable=False, index=True)
    method = Column(String(16), nullable=False)
    path = Column(String(512), nullable=False)
    request_hash = Column(String(64), nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    clinic_id = Column(Integer, nullable=True, index=True)
    status_code = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
