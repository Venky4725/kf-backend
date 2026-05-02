# app/schemas/task.py

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    batch_id: UUID
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    batch_id: UUID
    due_date: date | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True