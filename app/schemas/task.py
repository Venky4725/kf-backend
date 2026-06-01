# app/schemas/task.py

from pydantic import BaseModel, model_validator, field_validator, Field, AliasChoices
from uuid import UUID
from datetime import date, datetime
from typing import Literal, List, Optional
from app.schemas.weekly_plan import WeeklyPlanDayResponse

class RoadmapTask(BaseModel):
    day: str
    topic: str
    activities: str
    outcome: str

class RoadmapEntrySchema(BaseModel):
    day: str
    topic: str
    activities: str
    outcome: str

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    batch_id: UUID
    assigned_to: UUID | None = None  # NEW
    role: str | None = Field(default=None, validation_alias=AliasChoices("role", "tech_stack", "intern_role"))
    due_date: date | None = None
    priority: str | None = "MEDIUM"
    status: str | None = "OPEN"
    task_type: str | None = None
    roadmap_entries: List[RoadmapEntrySchema] | None = None

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        from app.utils.role_utils import normalize_role
        return normalize_role(v)
    
    @model_validator(mode='after')
    def validate_roadmap_fields(self) -> 'TaskCreate':
        if self.task_type == "roadmap":
            if not self.roadmap_entries or len(self.roadmap_entries) == 0:
                raise ValueError("roadmap_entries required for roadmap tasks")
        return self


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assigned_to: UUID | None = None  # NEW
    role: str | None = Field(default=None, validation_alias=AliasChoices("role", "tech_stack", "intern_role"))
    due_date: date | None = None
    priority: str | None = None
    status: str | None = None
    task_type: str | None = None
    roadmap_entries: List[RoadmapEntrySchema] | None = None

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        from app.utils.role_utils import normalize_role
        return normalize_role(v)


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    batch_id: UUID
    batch_name: str | None = None  # Enriched from Batch table
    assigned_to: UUID | None = None
    assigned_to_name: str | None = None  # Enriched from Profile table
    role: str | None = Field(default=None, validation_alias=AliasChoices("role", "tech_stack", "intern_role"))
    due_date: date | None
    priority: str | None = "MEDIUM"
    status: str | None = "OPEN"
    task_type: str | None = None
    type: str | None = None # task | roadmap
    roadmap_entries: List[RoadmapEntrySchema] | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    weekly_plan_days: Optional[List[WeeklyPlanDayResponse]] = None

    @model_validator(mode='after')
    def populate_type(self) -> 'TaskResponse':
        if self.task_type == "roadmap":
            self.type = "roadmap"
        else:
            self.type = "task"
        return self

    class Config:
        from_attributes = True


class TaskBulkCreate(BaseModel):
    batch_id: UUID
    assigned_to: UUID | None = None
    role: str | None = Field(default=None, validation_alias=AliasChoices("role", "tech_stack", "intern_role"))
    
    # Updated tasks field to support both strings and structured RoadmapTask objects
    tasks: List[RoadmapTask | str] | None = None
    due_date: date | None = None
    
    # New fields for Smart Import
    import_mode: Literal["simple", "roadmap"] | None = None
    content: str | None = None
    
    # Structured data
    task_type: str | None = None
    roadmap_entries: List[RoadmapEntrySchema] | None = None

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        from app.utils.role_utils import normalize_role
        return normalize_role(v)

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
        has_structured = self.task_type == "roadmap" and self.roadmap_entries is not None and len(self.roadmap_entries) > 0
        
        if not has_tasks and not has_smart and not has_structured:
            raise ValueError("No tasks provided. Provide 'tasks' list, 'import_mode' + 'content', or 'roadmap_entries'.")
            
        return self


class TaskBulkResponse(BaseModel):
    success: bool = True
    created: int
    failed: int = 0
    task_ids: list[UUID] = []