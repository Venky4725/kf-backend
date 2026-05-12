# app/schemas/evaluation.py

from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime


class EvaluationCreate(BaseModel):
    intern_id: UUID
    reviewed_by: UUID
    week_number: int
    score: float
    feedback: str | None = None


class EvaluationUpdateTechLead(BaseModel):
    """Schema for TECHNICAL_LEAD - restricted fields only"""
    week_number: int | None = None
    score: float | None = None
    feedback: str | None = None
    
    @field_validator('week_number')
    @classmethod
    def validate_week_number(cls, v):
        if v is not None and v < 1:
            raise ValueError('Week number must be greater than or equal to 1')
        return v
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Score must be between 0 and 5')
        return v


class EvaluationUpdateAdmin(BaseModel):
    """Schema for ADMIN - all fields allowed"""
    week_number: int | None = None
    score: float | None = None
    feedback: str | None = None
    intern_id: UUID | None = None
    reviewed_by: UUID | None = None
    
    @field_validator('week_number')
    @classmethod
    def validate_week_number(cls, v):
        if v is not None and v < 1:
            raise ValueError('Week number must be greater than or equal to 1')
        return v
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Score must be between 0 and 5')
        return v


# Backward compatibility alias - defaults to admin schema
class EvaluationUpdate(EvaluationUpdateAdmin):
    """Backward compatibility - defaults to admin permissions"""
    pass


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