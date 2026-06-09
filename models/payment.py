from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=False, index=True)
    payment_id = Column(String, nullable=True, unique=True, index=True)  # Stripe PaymentIntent ID
    stripe_session_id = Column(String, nullable=True, index=True)  # Stripe Checkout session ID
    amount = Column(Integer, nullable=False, default=0)  # Smallest currency unit (Stripe amount)
    amount_refunded = Column(Integer, nullable=False, default=0)
    currency = Column(String, nullable=True, default="eur")
    status = Column(String, nullable=False, default="pending", index=True)
    refund_status = Column(String, nullable=False, default="none", index=True)  # none, partial, full
    settlement_channel = Column(String, nullable=True, index=True)
    last_stripe_event_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    appointment = relationship("RendezVous", back_populates="payments")