from pydantic import BaseModel


class PatientBase(BaseModel):
    first_name: str
    last_name: str
    age: int
    gender: str


class PatientCreate(PatientBase):
    pass


class PatientResponse(PatientBase):
    id: int

    class Config:
        from_attributes = True