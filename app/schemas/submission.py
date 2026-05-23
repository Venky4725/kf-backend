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
    # Joined batch data
    batch_id: UUID | None = None
    batch_name: str | None = None

    class Config:
        from_attributes = True


class SubmissionSummaryResponse(BaseModel):
    """Slimmer schema for listing views - truncates or excludes large content."""
    id: UUID
    user_id: UUID
    submitted_for: date
    content_preview: str | None = None  # Short preview instead of full content
    created_at: datetime
    submitted_by_name: str | None = None
    batch_id: UUID | None = None
    batch_name: str | None = None

    class Config:
        from_attributes = True
        populate_by_name = True
