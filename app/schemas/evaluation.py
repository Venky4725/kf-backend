# app/schemas/evaluation.py

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class EvaluationCreate(BaseModel):
    intern_id: UUID
    reviewed_by: UUID
    week_number: int
    score: float
    feedback: str | None = None


class EvaluationUpdate(BaseModel):
    score: float | None = None
    feedback: str | None = None


class EvaluationResponse(BaseModel):
    id: UUID
    intern_id: UUID
    reviewed_by: UUID
    week_number: int
    score: float
    feedback: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvaluationInternResponse(BaseModel):
    """Response schema for interns - excludes score field"""
    id: UUID
    intern_id: UUID
    reviewed_by: UUID
    week_number: int
    feedback: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True