from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
import re

from core.roles import assert_public_registration_role
from security import validate_password


class PublicRegistration(BaseModel):
    """
    Public self-service registration payload.
    Privileged roles (admin) are rejected at validation — not only at handler level.
    """

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    role: str = "patient"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email address")
        return email

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        validate_password(v)
        return v

    @field_validator("role")
    @classmethod
    def validate_public_role(cls, v: str) -> str:
        return assert_public_registration_role(v)


class AdminUserCreate(BaseModel):
    """Administrator provisioning (authenticated admin only)."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email address")
        return email

    @field_validator("password")
    @classmethod
    def validate_strong_password(cls, v: str) -> str:
        validate_password(v)
        return v


# Backward-compatible alias for imports; same constraints as PublicRegistration.
UserCreate = PublicRegistration


class UserLogin(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        validate_password(v)
        return v


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email address")
        return email


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        validate_password(v)
        return v


class PlatformOwnerSetupRequest(BaseModel):
    """First-time platform owner setup (only when no owner exists)."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    password_confirm: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email = v.strip().lower()
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Invalid email address")
        return email

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        validate_password(v)
        return v

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    user_role: str
    role: str
    email: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    doctor_id: Optional[int] = None
    full_name: Optional[str] = None
    clinic_id: Optional[int] = None
    clinic_name: Optional[str] = None
