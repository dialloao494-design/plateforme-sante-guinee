from pydantic import BaseModel


class DoctorBase(BaseModel):
    first_name: str
    last_name: str
    specialty: str
    location: str
    phone: str
    photo_url: str | None = None
    consultation_fee: float = 0.0


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    specialty: str | None = None
    location: str | None = None
    phone: str | None = None
    photo_url: str | None = None
    consultation_fee: float | None = None


class DoctorResponse(BaseModel):
    id: int
    name: str
    specialty: str

    class Config:
        orm_mode = True
