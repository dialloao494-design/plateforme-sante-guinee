from sqlalchemy import Column, Integer, String
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    prenom = Column(String, index=True)
    age = Column(Integer)
    sexe = Column(String)
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class RendezVous(Base):
    __tablename__ = "rendezvous"

    class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    prenom = Column(String)
    age = Column(Integer)
    sexe = Column(String)

    rendezvous = relationship("RendezVous", back_populates="patient")