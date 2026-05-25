# app/schemas/auth.py

from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    user: "UserInfo"


class UserInfo(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    intern_role: str | None = None
    tech_stack: str | None
    batch_id: UUID | None

    class Config:
        from_attributes = True


LoginResponse.model_rebuild()


class ChangePasswordRequest(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    """Simple internal flow - resets password to default."""
    email: EmailStr


class AdminCreateUserRequest(BaseModel):
    """Admin endpoint to create new users."""
    name: str
    email: EmailStr
    role: str
    intern_role: str | None = None
    tech_stack: str | None = None
    batch_id: UUID | None = None

    @field_validator('intern_role')
    @classmethod
    def validate_intern_role(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        
        normalized = v.strip().upper()
        if normalized in {"AIML", "AI/ML", "AI-ML"}:
            return "AI/ML"
        elif normalized in {"FULL STACK", "FULLSTACK", "FULL-STACK"}:
            return "FULLSTACK"
        
        raise ValueError('Intern role must be either AI/ML or FULLSTACK')


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
