# app/routers/tasks.py

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskResponse])
def get_tasks(
    skip: int = 0,
    limit: int = 100,
    batch_id: UUID | None = None,
    db: Session = Depends(get_db),
):
    return task_service.list_tasks(db, skip=skip, limit=limit, batch_id=batch_id)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
):
    return task_service.get(db, task_id)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
):
    return task_service.create_task(db, payload)


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
):
    return task_service.update_task(db, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    task_service.delete(db, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
