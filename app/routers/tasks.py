# app/routers/tasks.py

from uuid import UUID
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate, TaskBulkCreate, TaskBulkResponse
from app.services.task_service import task_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])
logger = logging.getLogger(__name__)


@router.post("/bulk", response_model=TaskBulkResponse, status_code=status.HTTP_201_CREATED)
def create_tasks_bulk(
    payload: TaskBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        from fastapi.encoders import jsonable_encoder
        logger.info(f"Bulk task creation request from {current_user.email if current_user else 'unknown'}: {jsonable_encoder(payload)}")
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return task_service.create_tasks_bulk(db, payload, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_tasks_bulk: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tasks: {str(e)}"
        )


@router.get("", response_model=list[TaskResponse])
def get_tasks(
    skip: int = 0,
    limit: int = 100,
    batch_id: UUID | None = None,
    role: str | None = None,
    search: str | None = None,
    due_date: date | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return task_service.list_tasks(
            db,
            skip=skip,
            limit=limit,
            batch_id=batch_id,
            role=role,
            search=search,
            due_date=due_date,
            sort_by=sort_by,
            order=order,
            current_user=current_user,
        )
    except Exception as e:
        logger.error(f"Error in get_tasks: {e}")
        # Return empty list instead of crashing
        return []


@router.get("/my", response_model=list[TaskResponse])
def get_my_tasks(
    due_date: date | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Fetch tasks assigned to the logged-in intern.
    Includes both individual tasks and roadmap tasks relevant to their role and batch.
    """
    try:
        return task_service.list_tasks(
            db,
            due_date=due_date,
            search=search,
            current_user=current_user,
        )
    except Exception as e:
        logger.error(f"Error in get_my_tasks: {e}")
        # Return empty list instead of crashing
        return []


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        return task_service.get(db, task_id)
    except Exception as e:
        logger.error(f"Error in get_task: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return task_service.create_task(db, payload, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        return task_service.update_task(db, task_id, payload, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    try:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        task_service.delete(db, task_id, current_user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )
