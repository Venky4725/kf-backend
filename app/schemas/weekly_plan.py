from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class WeeklyPlanDayBase(BaseModel):
    day: str = Field(..., description="The day of the plan, e.g., Mon May 26")
    topic: str = Field(..., description="The main topic or theme for the day")
    activities: Optional[str] = None
    outcome: Optional[str] = None
    order_index: int = 0

class WeeklyPlanDayCreate(WeeklyPlanDayBase):
    pass

class WeeklyPlanDayResponse(WeeklyPlanDayBase):
    id: UUID
    task_id: UUID

    class Config:
        from_attributes = True

class WeeklyPlanCreateRequest(BaseModel):
    task_id: UUID
    days: List[WeeklyPlanDayCreate]
