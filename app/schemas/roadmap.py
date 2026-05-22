# app/schemas/roadmap.py

from pydantic import BaseModel, ConfigDict
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
