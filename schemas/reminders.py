"""Pydantic schemas for appointment reminders."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ReminderResponseRequest(BaseModel):
    action: str
    payload: Optional[str] = None
    token: Optional[str] = None


class ReminderEventResponse(BaseModel):
    id: int
    event_type: str
    created_at: datetime
    appointment_id: Optional[int]
    patient_id: Optional[int]
    appointment_date: Optional[str] = None

    class Config:
        from_attributes = True


class StaffNotificationItem(BaseModel):
    id: int
    event_type: str
    created_at: str
    appointment_id: Optional[int]
    patient_id: Optional[int]
    appointment_date: Optional[str]
