# app/schemas/notification.py

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class NotificationCreate(BaseModel):
    user_id: UUID
    title: str
    message: str
    type: str | None = None
    sender_id: UUID | None = None  # NEW


class NotificationBroadcast(BaseModel):
    message: str
    type: str = "SYSTEM"


class NotificationUpdate(BaseModel):
    is_read: bool


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    sender_id: UUID | None = None  # NEW
    sender_name: str | None = None  # NEW - computed field
    is_sender: bool = False  # NEW - indicates if current user is the sender
    title: str
    message: str
    type: str | None = None
    is_read: bool
    is_broadcast: bool | None = None
    created_at: datetime

    class Config:
        from_attributes = True