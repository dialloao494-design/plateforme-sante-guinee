from datetime import datetime

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: int
    channel: str
    subject: str
    body: str
    meta: str | None = None
    created_at: datetime

    class Config:
        orm_mode = True
