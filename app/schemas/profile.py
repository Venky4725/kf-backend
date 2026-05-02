# app/schemas/profile.py

from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class ProfileCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    tech_stack: str | None = None
    batch_id: UUID | None = None


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
