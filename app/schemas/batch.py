# app/schemas/batch.py

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime


class BatchCreate(BaseModel):
    name: str
    tech_stack: str
    start_date: date
    team_lead_id: UUID | None = None


class BatchUpdate(BaseModel):
    name: str | None = None
    tech_stack: str | None = None
    start_date: date | None = None
    team_lead_id: UUID | None = None


class BatchResponse(BaseModel):
    id: UUID
    name: str
    tech_stack: str
    start_date: date
    team_lead_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True