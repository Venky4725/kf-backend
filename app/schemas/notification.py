# app/schemas/notification.py

from pydantic import BaseModel, model_validator
from uuid import UUID
from datetime import datetime
from typing import Any


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
    title: str | None = None
    message: str | None = None
    is_read: bool | None = None
    type: str | None = None

    @model_validator(mode="before")
    @classmethod
    def handle_nested_notification(cls, data: Any) -> Any:
        if isinstance(data, dict) and "notification" in data:
            return data["notification"]
        return data


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
    edited_at: datetime | None = None  # NEW: Track when notification was edited

    class Config:
        from_attributes = True