# app/schemas/task.py

from pydantic import BaseModel, model_validator
from uuid import UUID
from datetime import date, datetime
from typing import Literal


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
    batch_id: UUID
    assigned_to: UUID | None = None
    
    # Legacy fields
    tasks: list[str] | None = None
    due_date: date | None = None
    
    # New fields for Smart Import
    import_mode: Literal["simple", "roadmap"] | None = None
    content: str | None = None

    @model_validator(mode='after')
    def validate_import_fields(self) -> 'TaskBulkCreate':
        if self.import_mode or self.content:
            if not self.import_mode or not self.content:
                raise ValueError("Both 'import_mode' and 'content' must be provided together.")
        elif not self.tasks:
            raise ValueError("Either 'tasks' or 'import_mode' + 'content' must be provided.")
        return self


class TaskBulkResponse(BaseModel):
    created: int
    failed: int
    task_ids: list[UUID]