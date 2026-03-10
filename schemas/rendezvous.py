from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RendezVousBase(BaseModel):
    date: datetime
    status: Optional[str] = "pending"
    doctor_id: int
    patient_id: int


class RendezVousCreate(RendezVousBase):
    pass


class RendezVousResponse(RendezVousBase):
    id: int

    class Config:
        orm_mode = True