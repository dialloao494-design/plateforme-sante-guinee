"""Unified invoices, line items, and payment records."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    visit_id = Column(Integer, ForeignKey("clinical_visits.id"), nullable=True, index=True)
    invoice_number = Column(String(32), nullable=False, unique=True, index=True)
    department = Column(String(128), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="draft", index=True)
    # draft | issued | partially_paid | paid | cancelled
    subtotal_amount_gnf = Column(Integer, nullable=False, default=0)
    exemption_percent = Column(Integer, nullable=False, default=0)
    exemption_amount_gnf = Column(Integer, nullable=False, default=0)
    total_amount_gnf = Column(Integer, nullable=False, default=0)
    paid_amount_gnf = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    issued_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    clinic = relationship("Clinic", back_populates="invoices")
    patient = relationship("Patient", back_populates="invoices")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    visit = relationship("ClinicalVisit", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("PaymentRecord", back_populates="invoice", cascade="all, delete-orphan")
    charges = relationship("ClinicCharge", foreign_keys="ClinicCharge.invoice_id", back_populates="invoice")
    refunds = relationship("ClinicRefund", back_populates="invoice")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    charge_type = Column(String(32), nullable=False, index=True)
    # consultation | laboratory | radiology | pharmacy | hospitalization | nursing | oxygen | procedure
    source_type = Column(String(32), nullable=False)
    source_id = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price_gnf = Column(Integer, nullable=False, default=0)
    amount_gnf = Column(Integer, nullable=False, default=0)
    clinic_charge_id = Column(Integer, ForeignKey("clinic_charges.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="items")
    clinic_charge = relationship("ClinicCharge", back_populates="invoice_item")


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    amount_gnf = Column(Integer, nullable=False)
    payment_method = Column(String(32), nullable=False)
    reference = Column(String(128), nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    paid_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", back_populates="payments")
