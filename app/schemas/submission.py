# app/schemas/submission.py

from pydantic import BaseModel
from uuid import UUID
from datetime import date, datetime


class SubmissionCreate(BaseModel):
    user_id: UUID
    submitted_for: date
    content: str


class SubmissionUpdate(BaseModel):
    content: str


class SubmissionResponse(BaseModel):
    id: UUID
    user_id: UUID
    submitted_for: date
    content: str
    created_at: datetime
    # Joined profile data for submitted by name
    submitted_by_name: str | None = None
    # Joined batch data for batch name (NEW)
    batch_name: str | None = None

    class Config:
        from_attributes = True
