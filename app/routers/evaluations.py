# app/routers/evaluations.py

from uuid import UUID
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.evaluation import (
    EvaluationCreate, 
    EvaluationResponse, 
    EvaluationUpdate,
    EvaluationInternResponse
)
from app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.get("", response_model=Union[list[EvaluationResponse], list[EvaluationInternResponse]])
def get_evaluations(
    skip: int = 0,
    limit: int = 100,
    intern_id: UUID | None = None,
    reviewed_by: UUID | None = None,
    week_number: int | None = None,
    search: str | None = None,
    batch_id: UUID | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get evaluations with role-based filtering.
    - INTERN: Cannot see scores (only feedback)
    - TECH_LEAD/ADMIN: Can see all fields including scores
    """
    evaluations = evaluation_service.list_evaluations(
        db,
        skip=skip,
        limit=limit,
        intern_id=intern_id,
        reviewed_by=reviewed_by,
        week_number=week_number,
        search=search,
        batch_id=batch_id,
        sort_by=sort_by,
        order=order,
    )
    
    # Return different response based on role
    if current_user.role == "INTERN":
        # Interns should not see scores
        return [EvaluationInternResponse.model_validate(e) for e in evaluations]
    else:
        # Tech Leads and Admins can see full data including scores
        return [EvaluationResponse.model_validate(e) for e in evaluations]


@router.get("/{evaluation_id}", response_model=Union[EvaluationResponse, EvaluationInternResponse])
def get_evaluation(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get single evaluation with role-based filtering.
    - INTERN: Cannot see score
    - TECH_LEAD/ADMIN: Can see all fields including score
    """
    evaluation = evaluation_service.get(db, evaluation_id)
    
    # Return different response based on role
    if current_user.role == "INTERN":
        return EvaluationInternResponse.model_validate(evaluation)
    else:
        return EvaluationResponse.model_validate(evaluation)


@router.post("", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
def create_evaluation(
    payload: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return evaluation_service.create_evaluation(db, payload, current_user)


@router.put("/{evaluation_id}", response_model=EvaluationResponse)
def update_evaluation(
    evaluation_id: UUID,
    payload: EvaluationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return evaluation_service.update_evaluation(db, evaluation_id, payload, current_user)


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    evaluation_service.delete(db, evaluation_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
