"""Clinic-scoped pharmacy replenishment orders."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class PharmacyStockOrder(Base):
    __tablename__ = "pharmacy_stock_orders"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    inventory_item_id = Column(Integer, ForeignKey("pharmacy_inventory.id"), nullable=True, index=True)
    medication_name = Column(String(255), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    supplier = Column(String(128), nullable=False)
    status = Column(String(24), nullable=False, default="ordered", index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    received_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ordered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    inventory_item = relationship("PharmacyInventoryItem")

