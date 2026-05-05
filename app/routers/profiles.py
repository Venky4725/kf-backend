# app/routers/profiles.py

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status, UploadFile, File
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
    current_user=Depends(auth_get_current_user),
):
    """Create a new profile with required batch_name."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Creating profile with payload: {payload.model_dump()}")
    logger.info(f"Current user: {current_user.id} ({current_user.role})")
    return profile_service.create_profile(db, payload, current_user)


@router.put("/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: UUID,
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(auth_get_current_user),
):
    """Update a profile with access control."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"PUT /profiles/{profile_id} - Payload: {payload.model_dump(exclude_unset=True)}")
    logger.info(f"Current user: {current_user.id} ({current_user.role})")
    
    result = profile_service.update_profile(db, profile_id, payload, current_user)
    
    logger.info(f"Update successful - Returning: name={result.name}, email={result.email}, tech_stack={result.tech_stack}, batch_id={result.batch_id}")
    return result


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


@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(auth_get_current_user),
):
    """
    Upload CSV file to bulk create profiles.
    CSV format: name,email,role,tech_stack,batch_name
    """
    import logging
    import csv
    import io
    
    logger = logging.getLogger(__name__)
    logger.info(f"CSV upload initiated by user: {current_user.id} ({current_user.role})")
    
    # Check file type
    if not file.filename.endswith('.csv'):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )
    
    # Read file content
    try:
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading CSV file: {str(e)}"
        )
    
    created = 0
    skipped = 0
    errors = []
    
    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
        try:
            # Validate required fields
            if not row.get("name") or not row["name"].strip():
                skipped += 1
                errors.append(f"Row {row_num}: Missing name")
                continue
            
            if not row.get("email") or not row["email"].strip():
                skipped += 1
                errors.append(f"Row {row_num}: Missing email")
                continue
            
            if not row.get("role") or not row["role"].strip():
                skipped += 1
                errors.append(f"Row {row_num}: Missing role")
                continue
            
            # CRITICAL: Validate batch_name is present
            if not row.get("batch_name") or not row["batch_name"].strip():
                skipped += 1
                errors.append(f"Row {row_num}: Missing batch_name")
                logger.warning(f"Row {row_num} skipped: Missing batch_name")
                continue
            
            # Create profile
            profile_data = ProfileCreate(
                name=row["name"].strip(),
                email=row["email"].strip(),
                role=row["role"].strip(),
                tech_stack=row.get("tech_stack", "").strip() or None,
                batch_name=row["batch_name"].strip()
            )
            
            profile_service.create_profile(db, profile_data, current_user)
            created += 1
            logger.info(f"Row {row_num}: Created profile for {row['email']}")
            
        except Exception as e:
            skipped += 1
            error_msg = f"Row {row_num}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            continue
    
    logger.info(f"CSV upload complete: {created} created, {skipped} skipped")
    
    return {
        "created": created,
        "skipped": skipped,
        "errors": errors[:20]  # Limit to first 20 errors
    }
