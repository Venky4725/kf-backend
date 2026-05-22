# app/schemas/task.py

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    batch_id: UUID
    assigned_to: UUID | None = None  # NEW
    due_date: date | None = None
    priority: str | None = "MEDIUM"
    status: str | None = "OPEN"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: UUID | None = None  # NEW
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    batch_id: UUID
    batch_name: str | None = None  # Enriched from Batch table
    assigned_to: UUID | None = None
    assigned_to_name: str | None = None  # Enriched from Profile table
    due_date: date | None
    priority: str | None = "MEDIUM"
    status: str | None = "OPEN"
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBulkCreate(BaseModel):
    tasks: list[str]
    batch_id: UUID
    due_date: date | None = None
    assigned_to: UUID | None = None


class TaskBulkResponse(BaseModel):
    created: int
    failed: int
    task_ids: list[UUID]