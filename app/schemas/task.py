# app/schemas/task.py

from pydantic import BaseModel, model_validator, field_validator
from uuid import UUID
from datetime import date, datetime
from typing import Literal, List, Optional
from app.schemas.weekly_plan import WeeklyPlanDayResponse

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
    weekly_plan_days: Optional[List[WeeklyPlanDayResponse]] = None

    class Config:
        from_attributes = True


class TaskBulkCreate(BaseModel):
    batch_id: UUID
    assigned_to: UUID | None = None
    
    # Legacy fields
    tasks: list[str | None] | None = None
    due_date: date | None = None
    
    # New fields for Smart Import
    import_mode: Literal["simple", "roadmap"] | None = None
    content: str | None = None

    @field_validator('tasks')
    @classmethod
    def validate_tasks(cls, v: list[str | None] | None) -> list[str] | None:
        if v is None:
            return None
        # Ensure all elements are strings and not None
        return [str(t) for t in v if t is not None]

    @model_validator(mode='after')
    def validate_import_fields(self) -> 'TaskBulkCreate':
        # If any smart import field is provided, both must be provided
        if self.import_mode is not None or self.content is not None:
            if self.import_mode is None:
                raise ValueError("Missing 'import_mode' for smart import.")
            if self.content is None:
                raise ValueError("Missing 'content' for smart import.")
        
        # Ensure at least one import method is valid
        has_tasks = self.tasks is not None and len(self.tasks) > 0
        has_smart = self.import_mode is not None and self.content is not None
        
        if not has_tasks and not has_smart:
            raise ValueError("No tasks provided. Provide 'tasks' list or 'import_mode' + 'content'.")
            
        return self


class TaskBulkResponse(BaseModel):
    created: int
    failed: int
    task_ids: list[UUID]