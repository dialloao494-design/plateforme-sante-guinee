"""Laboratory result — validated output for a lab order."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    lab_order_id = Column(Integer, ForeignKey("lab_orders.id"), nullable=False, unique=True, index=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    result_summary = Column(Text, nullable=False)
    result_data = Column(Text, nullable=True)  # JSON string for structured values
    reference_range = Column(String(255), nullable=True)
    interpretation = Column(Text, nullable=True)

    status = Column(String(16), default="draft", nullable=False, index=True)  # draft | validated
    validated_at = Column(DateTime, nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    lab_order = relationship("LabOrder", back_populates="results")
