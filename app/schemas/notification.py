# app/schemas/notification.py

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class NotificationCreate(BaseModel):
    user_id: UUID
    title: str
    message: str


class NotificationUpdate(BaseModel):
    is_read: bool


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True