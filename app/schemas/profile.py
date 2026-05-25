# app/schemas/profile.py

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime


class ProfileCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    intern_role: Optional[str] = None  # AI/ML, FULLSTACK
    tech_stack: Optional[str] = None
    batch_id: Optional[UUID] = Field(None, validation_alias="batch")  # Accept both "batch_id" and "batch"
    batch_name: Optional[str] = None  # For CSV upload (batch lookup/creation)
    
    model_config = {
        "populate_by_name": True,  # Allow both field name and alias
    }
    
    @field_validator('intern_role')
    @classmethod
    def validate_intern_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        from app.utils.role_utils import normalize_role
        normalized = normalize_role(v)
        if normalized not in {"AIML", "FULLSTACK"}:
            raise ValueError('Intern role must be either AIML or FULLSTACK')
        return normalized

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate and normalize role to uppercase"""
        if not v or not v.strip():
            raise ValueError('Role cannot be empty')
        
        normalized = v.strip().upper()
        valid_roles = {'ADMIN', 'TECHNICAL_LEAD', 'INTERN'}
        
        if normalized not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(sorted(valid_roles))}')
        
        return normalized
    
    @model_validator(mode='after')
    def validate_intern_has_batch(self):
        """
        Ensure INTERN role has either batch_id or batch_name.
        This runs AFTER all field validators and field population.
        At this point, self.batch_id contains the parsed UUID (from either 'batch' or 'batch_id' field).
        """
        # Role is already normalized to uppercase by field validator
        if self.role == 'INTERN':
            # Check if EITHER batch_id OR batch_name is provided
            has_batch_id = self.batch_id is not None
            has_batch_name = self.batch_name is not None and self.batch_name.strip()
            
            if not has_batch_id and not has_batch_name:
                raise ValueError('Batch is required for INTERN role. Provide either batch_id or batch_name.')
        
        return self


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    intern_role: Optional[str] = None
    tech_stack: Optional[str] = None
    batch_id: Optional[UUID] = None
    batch_ids: Optional[list[UUID]] = None

    @field_validator('intern_role')
    @classmethod
    def validate_intern_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        from app.utils.role_utils import normalize_role
        normalized = normalize_role(v)
        if normalized not in {"AIML", "FULLSTACK"}:
            raise ValueError('Intern role must be either AIML or FULLSTACK')
        return normalized


class BatchShort(BaseModel):
    """Short batch information for technical lead assignment display"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


class ProfileListResponse(BaseModel):
    """Slimmer schema for listing views - excludes heavy auth fields."""
    id: UUID
    name: str
    email: EmailStr
    role: str
    intern_role: Optional[str] = None
    tech_stack: Optional[str] = None
    batch_id: Optional[UUID] = None
    batch_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ProfileResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    intern_role: Optional[str] = None
    tech_stack: Optional[str]
    batch_id: Optional[UUID]
    batch_name: Optional[str] = None  # Added for consistency
    # For Technical Leads: all assigned batches
    batches: list[BatchShort] = Field(default=[], validation_alias="led_batches")
    # Authentication fields
    must_change_password: bool
    is_active: bool
    password_changed_at: Optional[datetime]
    last_login_at: Optional[datetime]
    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }
