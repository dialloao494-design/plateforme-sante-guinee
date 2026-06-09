from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("rendezvous.id"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=True)
    attachment_name = Column(String, nullable=True)
    # Deprecated — legacy public URL; never expose in API responses.
    attachment_url = Column(String, nullable=True)
    attachment_storage_key = Column(String, nullable=True, index=True)
    attachment_mime_type = Column(String, nullable=True)
    attachment_size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    appointment = relationship("RendezVous", back_populates="messages")
    sender = relationship("User")

    @property
    def sender_role(self) -> str:
        return getattr(self.sender, "role", "") or ""
