# app/routers/profiles.py

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.dependencies import get_current_user as auth_get_current_user
from app.core.dependencies import oauth2_scheme
from app.schemas.auth import AdminCreateUserRequest, MessageResponse
from app.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.services.auth_service import auth_service
from app.services.profile_service import profile_service

router = APIRouter(prefix="/profiles", tags=["Profiles"])


@router.get("", response_model=list[ProfileResponse])
def get_profiles(
    skip: int = 0,
    limit: int = 100,
    role: str | None = None,
    batch_id: UUID | None = None,
    search_name: str | None = None,
    search_email: str | None = None,
    tech_stack: str | None = None,
    sort_by: str | None = None,
    sort_order: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    return profile_service.list_profiles(
        db,
        skip=skip,
        limit=limit,
        role=role,
        batch_id=batch_id,
        search_name=search_name,
        search_email=search_email,
        tech_stack=tech_stack,
        sort_by=sort_by,
        sort_order=sort_order,
        is_active=is_active,
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
def get_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
):
    return profile_service.get(db, profile_id)


@router.post("", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
):
    """Create a new profile."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Creating profile with payload: {payload.model_dump()}")
    return profile_service.create_profile(db, payload)


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: UUID,
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
):
    return profile_service.update_profile(db, profile_id, payload)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    """
    Delete a profile with dependency checking.
    Will fail if profile has dependencies (batches, evaluations, submissions, notifications).
    Use PATCH /{profile_id}/deactivate for soft delete instead.
    """
    profile_service.delete_profile(db, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{profile_id}/deactivate", response_model=ProfileResponse)
def deactivate_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Soft delete: deactivate a profile (sets is_active=false).
    Preserves data integrity and history. User cannot login when deactivated.
    """
    return profile_service.deactivate_profile(db, profile_id)


@router.patch("/{profile_id}/activate", response_model=ProfileResponse)
def activate_profile(
    profile_id: UUID,
    db: Session = Depends(get_db),
):
    """Reactivate a deactivated profile (sets is_active=true)."""
    return profile_service.activate_profile(db, profile_id)


# Admin endpoints - protected with role check
@router.post("/users/create", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: AdminCreateUserRequest,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Admin endpoint to create new user with default password. Requires ADMIN role."""
    # First verify the user is authenticated and has admin role
    current_user = auth_service.get_current_user(db, token)
    if current_user.role.upper() != "ADMIN":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create new users.",
        )
    return auth_service.create_user(db, payload)
