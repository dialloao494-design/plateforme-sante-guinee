from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: str
    subject: str
    body: str
    meta: str | None = None
    created_at: datetime
