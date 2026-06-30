"""Split payment rows for in-clinic charges (pharmacy, etc.)."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class ClinicChargePayment(Base):
    __tablename__ = "clinic_charge_payments"

    id = Column(Integer, primary_key=True, index=True)
    charge_id = Column(Integer, ForeignKey("clinic_charges.id"), nullable=False, index=True)
    amount_gnf = Column(Integer, nullable=False)
    payment_method = Column(String(32), nullable=False)
    reference = Column(String(128), nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    charge = relationship("ClinicCharge", back_populates="payments")
