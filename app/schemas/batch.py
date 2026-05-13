# app/schemas/batch.py

from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import date, datetime


class BatchCreate(BaseModel):
    name: str
    tech_stack: str
    start_date: date
    first_tech_lead_id: UUID | None = None
    second_tech_lead_id: UUID | None = None
    
    @field_validator('second_tech_lead_id')
    @classmethod
    def validate_tech_leads_different(cls, v, info):
        """Ensure first and second tech leads are different"""
        if v is not None and 'first_tech_lead_id' in info.data:
            first_tl = info.data.get('first_tech_lead_id')
            if first_tl is not None and v == first_tl:
                raise ValueError('First and second tech leads must be different')
        return v


class BatchUpdate(BaseModel):
    name: str | None = None
    tech_stack: str | None = None
    start_date: date | None = None
    first_tech_lead_id: UUID | None = None
    second_tech_lead_id: UUID | None = None
    
    @field_validator('second_tech_lead_id')
    @classmethod
    def validate_tech_leads_different(cls, v, info):
        """Ensure first and second tech leads are different"""
        if v is not None and 'first_tech_lead_id' in info.data:
            first_tl = info.data.get('first_tech_lead_id')
            if first_tl is not None and v == first_tl:
                raise ValueError('First and second tech leads must be different')
        return v


class BatchResponse(BaseModel):
    id: UUID
    name: str
    tech_stack: str
    start_date: date
    first_tech_lead_id: UUID | None
    second_tech_lead_id: UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True