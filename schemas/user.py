from pydantic import BaseModel, validator
from typing import Optional
import re


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "patient"

    @validator("email")
    def validate_email(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email address")
        return email

    @validator("password")
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

    @validator("role")
    def validate_role(cls, v: str) -> str:
        role = v.strip().lower()
        if role not in {"patient", "doctor", "admin"}:
            raise ValueError("Role must be one of: patient, doctor, admin")
        return role


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    user_role: str
    role: str
    email: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    doctor_id: Optional[int] = None

    class Config:
        orm_mode = True
