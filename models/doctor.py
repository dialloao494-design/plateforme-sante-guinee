from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    specialty = Column(String)

    rendezvous = relationship("RendezVous", back_populates="doctor")