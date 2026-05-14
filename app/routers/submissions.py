# app/routers/submissions.py

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.submission import SubmissionCreate, SubmissionResponse, SubmissionUpdate
from app.services.submission_service import submission_service

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.get("", response_model=list[SubmissionResponse])
def get_submissions(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID | None = None,
    submitted_for: date | None = None,
    search: str | None = None,
    batch_id: UUID | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return submission_service.list_submissions(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        submitted_for=submitted_for,
        search=search,
        batch_id=batch_id,
        sort_by=sort_by,
        order=order,
        current_user=current_user,
    )


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: UUID,
    db: Session = Depends(get_db),
):
    submission = submission_service.get(db, submission_id)
    
    # Enrich with batch info
    try:
        profile = db.query(submission_service.model.__table__.c.user_id).first()
        from app.models.profile import Profile
        from app.models.batch import Batch
        
        profile = db.get(Profile, submission.user_id)
        if profile:
            submission.submitted_by_name = profile.name
            submission.batch_id = profile.batch_id
            if profile.batch_id:
                batch = db.get(Batch, profile.batch_id)
                submission.batch_name = batch.name if batch else None
            else:
                submission.batch_name = None
        else:
            submission.submitted_by_name = None
            submission.batch_id = None
            submission.batch_name = None
    except Exception:
        submission.submitted_by_name = None
        submission.batch_id = None
        submission.batch_name = None
    
    return submission


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
):
    return submission_service.create_submission(db, payload)


@router.put("/{submission_id}", response_model=SubmissionResponse)
def update_submission(
    submission_id: UUID,
    payload: SubmissionUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return submission_service.update_submission(db, submission_id, payload, current_user)


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    submission_service.delete(db, submission_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
