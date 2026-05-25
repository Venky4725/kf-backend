# app/services/auth_service.py

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    password_strength_ok,
    verify_password,
)
from app.models.profile import Profile
from app.schemas.auth import (
    AdminCreateUserRequest,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    UserInfo,
)

# Default password for new users
DEFAULT_PASSWORD = "Welcome@123"


class AuthService:
    """
    Authentication service using database-based password hashing.
    Uses the public.profiles table as the authentication source.
    """

    def login(self, db: Session, payload: LoginRequest) -> LoginResponse:
        """Authenticate user and return JWT token."""
        # Find user by email
        profile = db.query(Profile).filter(
            Profile.email == payload.email.strip().lower()
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact administrator.",
            )

        # Verify password
        if not verify_password(payload.password, profile.password_hash or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login timestamp
        profile.last_login_at = datetime.utcnow()
        db.commit()

        # Generate JWT token
        access_token = create_access_token(
            subject=str(profile.id),
            role=profile.role,
            extra={"email": profile.email, "name": profile.name},
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            must_change_password=profile.must_change_password,
            user=UserInfo(
                id=profile.id,
                name=profile.name,
                email=profile.email,
                role=profile.role,
                intern_role=profile.intern_role,
                tech_stack=profile.tech_stack,
                batch_id=profile.batch_id,
            ),
        )

    def get_current_user(self, db: Session, token: str | None = None) -> Profile:
        """Get current authenticated user from JWT token."""
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials were not provided.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Decode JWT token
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract profile ID from token
        profile_id = payload.get("sub")
        if not profile_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch profile from database
        try:
            profile_uuid = UUID(profile_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        profile = db.query(Profile).filter(Profile.id == profile_uuid).first()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authenticated account is not found.",
            )

        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact administrator.",
            )

        return profile

    def require_roles(self, db: Session, token: str | None = None, *roles: str) -> Profile:
        """Require specific roles for access."""
        profile = self.get_current_user(db, token)
        normalized_roles = {role.strip().upper() for role in roles}
        if normalized_roles and profile.role.upper() not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return profile

    def change_password(
        self, db: Session, payload: ChangePasswordRequest
    ) -> dict[str, Any]:
        """Change user password."""
        # Find user by email
        profile = db.query(Profile).filter(
            Profile.email == payload.email.strip().lower()
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Verify old password
        if not verify_password(payload.old_password, profile.password_hash or ""):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect.",
            )

        # Check password strength
        is_strong, message = password_strength_ok(payload.new_password)
        if not is_strong:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message,
            )

        # Hash and update new password
        profile.password_hash = hash_password(payload.new_password)
        profile.must_change_password = False
        profile.password_changed_at = datetime.utcnow()
        db.commit()

        return {"message": "Password changed successfully."}

    def reset_password(
        self, db: Session, payload: ResetPasswordRequest
    ) -> dict[str, Any]:
        """Reset password to default (internal flow)."""
        # Find user by email
        profile = db.query(Profile).filter(
            Profile.email == payload.email.strip().lower()
        ).first()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Reset to default password
        profile.password_hash = hash_password(DEFAULT_PASSWORD)
        profile.must_change_password = True
        profile.password_changed_at = datetime.utcnow()
        db.commit()

        return {"message": "Password reset successfully. User must change password on next login."}

    def create_user(
        self, db: Session, payload: AdminCreateUserRequest
    ) -> Profile:
        """Admin endpoint to create new user with default password."""
        # Check if email already exists
        existing = db.query(Profile).filter(
            Profile.email == payload.email.strip().lower()
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists.",
            )

        # Generate password hash for default password
        password_hash = hash_password(DEFAULT_PASSWORD)
        
        # DEBUG: Log hash details
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[DEBUG] Generated password hash: {password_hash[:20]}...")
        logger.info(f"[DEBUG] Hash length: {len(password_hash)} chars")

        # Create new profile with default password
        profile = Profile(
            id=UUID(int=uuid4().int),
            name=payload.name,
            email=payload.email.strip().lower(),
            role=payload.role.upper(),
            intern_role=payload.intern_role,
            tech_stack=payload.tech_stack,
            batch_id=payload.batch_id,
            password_hash=password_hash,
            must_change_password=True,
            is_active=True,
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

        return profile


auth_service = AuthService()
