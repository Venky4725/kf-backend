# app/routers/auth.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, oauth2_scheme
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
)
from app.schemas.profile import ProfileResponse
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate user and return JWT token."""
    return auth_service.login(db, payload)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
):
    """Change user password (requires old password verification)."""
    return auth_service.change_password(db, payload)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset password to default (internal flow - admin use)."""
    return auth_service.reset_password(db, payload)


@router.get("/me", response_model=ProfileResponse)
def me(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Get current authenticated user."""
    return auth_service.get_current_user(db, token)
