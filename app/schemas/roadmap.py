# app/schemas/roadmap.py

from pydantic import BaseModel, ConfigDict, field_validator
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
    role: Optional[str] = None

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        
        normalized = v.strip().upper()
        if normalized in {"AIML", "AI/ML", "AI-ML"}:
            return "AI/ML"
        elif normalized in {"FULL STACK", "FULLSTACK", "FULL-STACK"}:
            return "FULLSTACK"
        
        # If it's "ALL", we can either keep it or normalize it.
        # But the user says "NOT: ALL".
        # If they mean they want to avoid "ALL" as a default, 
        # let's see if we should convert "ALL" to None (global).
        if normalized == "ALL":
            return None # Treat "ALL" as global (None) to avoid the string "ALL" if requested
            
        return normalized


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
