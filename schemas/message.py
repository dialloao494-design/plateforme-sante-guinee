from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: Optional[str] = Field(None, description="Message body")


class MessageResponse(BaseModel):
    id: int
    appointment_id: int
    sender_user_id: int
    sender_role: str
    content: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_url: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True
