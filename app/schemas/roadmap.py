# app/schemas/roadmap.py

from pydantic import BaseModel, ConfigDict, field_validator, Field, AliasChoices
from uuid import UUID
from datetime import datetime
from typing import List, Optional


class RoadmapEntryBase(BaseModel):
    day_label: str
    topic: str
    activities: Optional[str] = None
    outcome: Optional[str] = None
    sort_order: int = 0


class RoadmapEntryResponse(RoadmapEntryBase):
    id: UUID
    roadmap_id: UUID

    model_config = ConfigDict(from_attributes=True)


class WeeklyRoadmapBase(BaseModel):
    title: str
    batch_id: UUID
    role: str = Field(default="ALL", validation_alias=AliasChoices("role", "tech_stack", "intern_role"))

    model_config = ConfigDict(populate_by_name=True)

    @field_validator('role', mode='before')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        from app.utils.role_utils import normalize_role
        return normalize_role(v)

class RoadmapImportRequest(WeeklyRoadmapBase):
    content: str


class WeeklyRoadmapResponse(WeeklyRoadmapBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    entries: List[RoadmapEntryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class WeeklyRoadmapShortResponse(WeeklyRoadmapBase):
    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoadmapBulkImportResponse(BaseModel):
    roadmap_id: UUID
    entries_count: int
    entries: List[RoadmapEntryResponse]


# Preview Schemas
class RoadmapPreviewEntry(BaseModel):
    day: str
    topic: str
    activities: Optional[str] = ""
    outcome: Optional[str] = ""


class RoadmapPreviewRequest(BaseModel):
    content: str


class RoadmapPreviewResponse(BaseModel):
    entries: List[RoadmapPreviewEntry]
    entries_count: int
