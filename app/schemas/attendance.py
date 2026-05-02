# app/schemas/attendance.py

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime


class AttendanceCreate(BaseModel):
    user_id: UUID
    day: date
    status: str


class AttendanceUpdate(BaseModel):
    status: str


class AttendanceResponse(BaseModel):
    id: UUID
    user_id: UUID
    day: date
    status: str
    created_at: datetime

    class Config:
        from_attributes = True