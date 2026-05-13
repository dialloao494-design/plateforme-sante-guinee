from typing import Literal

from pydantic import BaseModel, Field


class MobileMoneyInitRequest(BaseModel):
    appointment_id: int = Field(..., ge=1)
    provider: Literal["orange_gn", "mtn_gn"]
    msisdn: str | None = Field(None, description="MSISDN in international format, e.g. +224620000000")


class MobileMoneyInitResponse(BaseModel):
    status: str
    provider: str
    reference: str
    amount_gnf: float
    msisdn_masked: str | None = None
    live_mode: bool = False
    created_at: str
    next_step: str
