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
    third_tech_lead_id: UUID | None = None
    
    @field_validator('second_tech_lead_id', 'third_tech_lead_id')
    @classmethod
    def validate_tech_leads_different(cls, v, info):
        """Ensure all tech leads are different"""
        if v is None:
            return v
        
        # Get all tech lead IDs
        first_tl = info.data.get('first_tech_lead_id')
        second_tl = info.data.get('second_tech_lead_id')
        
        # Check against first tech lead
        if first_tl is not None and v == first_tl:
            raise ValueError('All tech leads must be different')
        
        # Check against second tech lead (for third_tech_lead_id)
        if info.field_name == 'third_tech_lead_id' and second_tl is not None and v == second_tl:
            raise ValueError('All tech leads must be different')
        
        return v


class BatchUpdate(BaseModel):
    name: str | None = None
    tech_stack: str | None = None
    start_date: date | None = None
    first_tech_lead_id: UUID | None = None
    second_tech_lead_id: UUID | None = None
    third_tech_lead_id: UUID | None = None
    
    @field_validator('second_tech_lead_id', 'third_tech_lead_id')
    @classmethod
    def validate_tech_leads_different(cls, v, info):
        """Ensure all tech leads are different"""
        if v is None:
            return v
        
        # Get all tech lead IDs
        first_tl = info.data.get('first_tech_lead_id')
        second_tl = info.data.get('second_tech_lead_id')
        
        # Check against first tech lead
        if first_tl is not None and v == first_tl:
            raise ValueError('All tech leads must be different')
        
        # Check against second tech lead (for third_tech_lead_id)
        if info.field_name == 'third_tech_lead_id' and second_tl is not None and v == second_tl:
            raise ValueError('All tech leads must be different')
        
        return v


class TechLeadInfo(BaseModel):
    """Tech lead information for batch response"""
    id: UUID
    name: str
    email: str


class BatchResponse(BaseModel):
    id: UUID
    name: str
    tech_stack: str
    start_date: date
    first_tech_lead_id: UUID | None
    second_tech_lead_id: UUID | None
    third_tech_lead_id: UUID | None = None
    # Tech lead details for frontend display
    first_tech_lead: TechLeadInfo | None = None
    second_tech_lead: TechLeadInfo | None = None
    third_tech_lead: TechLeadInfo | None = None
    # DEPRECATED: Use tech_leads_display instead
    technical_lead: str | None = None  # Backward compatibility
    # PRIMARY: Use this field for display
    tech_leads_display: str = "Unassigned"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True