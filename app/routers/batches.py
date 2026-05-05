# app/routers/batches.py

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.services.batch_service import batch_service

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.get("", response_model=list[BatchResponse])
def get_batches(
    skip: int = 0,
    limit: int = 100,
    team_lead_id: UUID | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Tech Lead can only see their assigned batches
    if current_user.role == "TECHNICAL_LEAD":
        team_lead_id = current_user.id
    return batch_service.list_batches(
        db,
        skip=skip,
        limit=limit,
        team_lead_id=team_lead_id,
        search=search,
        sort_by=sort_by,
        order=order,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
):
    return batch_service.get(db, batch_id)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
):
    return batch_service.create_batch(db, payload)


@router.put("/{batch_id}", response_model=BatchResponse)
def update_batch(
    batch_id: UUID,
    payload: BatchUpdate,
    db: Session = Depends(get_db),
):
    return batch_service.update_batch(db, batch_id, payload)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    batch_service.delete(db, batch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
