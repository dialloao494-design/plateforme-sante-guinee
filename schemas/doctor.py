from pydantic import BaseModel


class DoctorBase(BaseModel):
    user_id: int
    name: str
    specialty: str


class DoctorCreate(DoctorBase):
    pass


class DoctorResponse(DoctorBase):
    id: int

    class Config:
        from_attributes = True