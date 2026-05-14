# app/schemas/profile.py

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from uuid import UUID
from datetime import datetime


class ProfileCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    tech_stack: str | None = None
    batch_id: UUID | None = Field(None, validation_alias="batch")  # Accept both "batch_id" and "batch"
    batch_name: str | None = None  # For CSV upload (batch lookup/creation)
    
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
        """Ensure INTERN role has either batch_id or batch_name"""
        if self.role and self.role.upper() == 'INTERN':
            if not self.batch_id and not self.batch_name:
                raise ValueError('Batch is required for INTERN role. Provide either batch_id or batch_name.')
        return self


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    tech_stack: str | None = None
    batch_id: UUID | None = None


class ProfileResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    tech_stack: str | None
    batch_id: UUID | None
    # Authentication fields
    must_change_password: bool
    is_active: bool
    password_changed_at: datetime | None
    last_login_at: datetime | None
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
