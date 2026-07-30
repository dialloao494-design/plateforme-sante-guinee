from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class PatientDocument(Base):
    __tablename__ = "patient_documents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type_document = Column(String(64), nullable=False)
    # Opaque storage key (never expose in API responses).
    file_path = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(128), nullable=True)
    content_sha256 = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    patient = relationship("Patient", back_populates="documents")
    uploader = relationship("User")
