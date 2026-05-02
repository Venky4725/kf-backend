# app/routers/submissions.py

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionResponse,
    SubmissionUpdate,
)
from app.services.submission_service import submission_service

router = APIRouter(
    prefix="/submissions",
    tags=["Submissions"],
)


@router.get("", response_model=list[SubmissionResponse])
def get_submissions(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID | None = None,
    submitted_for: date | None = None,
    db: Session = Depends(get_db),
):
    return submission_service.list_submissions(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        submitted_for=submitted_for,
    )


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: UUID,
    db: Session = Depends(get_db),
):
    return submission_service.get(db, submission_id)


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
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
):
    return submission_service.update_submission(
        db,
        submission_id,
        payload,
    )


@router.delete(
    "/{submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_submission(
    submission_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    submission_service.delete(db, submission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
