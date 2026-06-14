"""Pharmacy inventory — clinic-scoped medication stock."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class PharmacyInventoryItem(Base):
    __tablename__ = "pharmacy_inventory"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    sku = Column(String(64), nullable=False, index=True)
    medication_name = Column(String(255), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    reorder_level = Column(Integer, nullable=False, default=10)
    unit_price_gnf = Column(Integer, nullable=False, default=25_000)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="pharmacy_inventory")
