from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    age = Column(Integer)
    gender = Column(String)

    rendezvous = relationship("RendezVous", back_populates="patient")