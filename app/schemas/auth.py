# app/schemas/auth.py

from pydantic import BaseModel, EmailStr
from uuid import UUID


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
    tech_stack: str | None = None
    batch_id: UUID | None = None


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
