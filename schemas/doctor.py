from pydantic import BaseModel
from typing import Optional


class DoctorBase(BaseModel):
    first_name: str
    last_name: str
    specialty: str
    location: str
    phone: str
    photo_url: str | None = None
    consultation_fee: float = 0.0


class DoctorCreate(DoctorBase):
    latitude: float | None = None
    longitude: float | None = None


class DoctorUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    specialty: str | None = None
    location: str | None = None
    phone: str | None = None
    photo_url: str | None = None
    consultation_fee: float | None = None
    latitude: float | None = None
    longitude: float | None = None


class DoctorGeoUpdate(BaseModel):
    """Practice coordinates for map / nearby discovery (doctor updates own profile)."""

    latitude: float | None = None
    longitude: float | None = None
    location: str | None = None


class DoctorResponse(BaseModel):
    """Public doctor response - safe for unauthenticated clients. Does NOT expose phone."""

    id: int
    name: str
    specialty: str
    location: str
    photo_url: Optional[str] = None
    consultation_fee: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None

    class Config:
        orm_mode = True


class DoctorDetailedResponse(BaseModel):
    """Internal doctor response - includes sensitive data (phone). Admin/Doctor only."""

    id: int
    name: str
    first_name: str
    last_name: str
    specialty: str
    location: str
    phone: str
    photo_url: Optional[str] = None
    consultation_fee: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        orm_mode = True
