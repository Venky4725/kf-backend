from uuid import UUID
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from sqlalchemy.exc import SQLAlchemyError

from app.models.batch import Batch
from app.models.profile import Profile
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError

logger = logging.getLogger(__name__)


class TaskService(CRUDService[Task]):
    model = Task
    resource_name = "Task"
    table_name = "tasks"

    def create_task(self, db: Session, payload: TaskCreate, current_user) -> Task:
        try:
            # Validate batch exists
            self._ensure_batch_exists(db, payload.batch_id)
            
            # Tech Lead can only create tasks for their assigned batches
            if current_user.role == "TECHNICAL_LEAD":
                # Check if tech lead is assigned to this batch (any TL position)
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, payload.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only create tasks for their assigned batches"
                    )
            
            # Validate assigned_to user exists (ALLOW CROSS-BATCH ASSIGNMENT)
            if payload.assigned_to:
                user = db.get(Profile, payload.assigned_to)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"User '{payload.assigned_to}' does not exist."
                    )
                if not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot assign task to inactive user"
                    )
            
            task_data = {
                "title": payload.title.strip() if payload.title else "",
                "description": payload.description,
                "batch_id": payload.batch_id,
                "due_date": payload.due_date,
            }
            
            # Add assigned_to if provided (handle missing column gracefully)
            if payload.assigned_to:
                try:
                    task_data["assigned_to"] = payload.assigned_to
                except Exception as e:
                    logger.warning(f"Could not set assigned_to field: {e}")
                    # Continue without assigned_to if column doesn't exist
            
            return self.create(db, task_data)
        except HTTPException:
            raise
        except ConflictError:
            raise
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create task"
            )

    def list_tasks(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        batch_id: UUID | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        order: str | None = None,
    ) -> list[Task]:
        try:
            # Validate skip and limit
            if skip is None or skip < 0:
                skip = 0
            if limit is None or limit < 1:
                limit = 100
            
            # If batch_id is provided, check if batch exists
            if batch_id:
                try:
                    batch = db.get(Batch, batch_id)
                    if not batch:
                        logger.warning(f"Batch {batch_id} not found, returning empty list")
                        return []
                except Exception as e:
                    logger.error(f"Error checking batch existence: {e}")
                    return []
            
            query = db.query(Task)
            
            # Filter by batch_id (only if provided and not None)
            if batch_id:
                query = query.filter(Task.batch_id == batch_id)
            
            # Search in title and description (only if provided and not empty)
            if search and search.strip():
                try:
                    search_pattern = f"%{search.strip()}%"
                    query = query.filter(
                        (Task.title.ilike(search_pattern)) |
                        (Task.description.ilike(search_pattern))
                    )
                except Exception as e:
                    logger.error(f"Error applying search filter: {e}")
                    # Continue without search filter
            
            # Sorting (with validation)
            VALID_SORT_FIELDS = {"title", "due_date", "created_at"}
            if sort_by and sort_by in VALID_SORT_FIELDS:
                try:
                    order_func = desc if order and order.lower() == "desc" else asc
                    if sort_by == "title":
                        query = query.order_by(order_func(Task.title))
                    elif sort_by == "due_date":
                        query = query.order_by(order_func(Task.due_date))
                    elif sort_by == "created_at":
                        query = query.order_by(order_func(Task.created_at))
                except Exception as e:
                    logger.error(f"Error applying sort: {e}")
                    # Continue with default sorting
                    query = query.order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.created_at.desc())
            else:
                # Default sorting
                query = query.order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.created_at.desc())
            
            # Execute query with pagination
            try:
                results = query.offset(skip).limit(limit).all()
                return results if results else []
            except SQLAlchemyError as e:
                logger.error(f"Database error executing query: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Unexpected error in list_tasks: {e}")
            # Always return empty list instead of crashing
            return []

    def update_task(self, db: Session, task_id: UUID, payload: TaskUpdate, current_user) -> Task:
        try:
            # Check if task exists
            task = self.get(db, task_id)
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
            
            # Check if batch exists
            batch = db.get(Batch, task.batch_id)
            if not batch:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Associated batch not found"
                )
            
            # Access control for Tech Lead
            if current_user.role == "TECHNICAL_LEAD":
                # Check if tech lead is assigned to this batch (any TL position)
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, task.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only update tasks in their assigned batches"
                    )
            
            # Validate assigned_to user exists (ALLOW CROSS-BATCH ASSIGNMENT)
            if payload.assigned_to:
                user = db.get(Profile, payload.assigned_to)
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"User '{payload.assigned_to}' does not exist."
                    )
                if not user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot assign task to inactive user"
                    )
            
            updates = payload.model_dump(exclude_unset=True)
            if "title" in updates and updates["title"] is not None:
                updates["title"] = updates["title"].strip()
            
            return self.update(db, task_id, updates)
        except HTTPException:
            raise
        except ConflictError:
            raise
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update task"
            )

    def delete(self, db: Session, task_id: UUID, current_user=None) -> None:
        try:
            # Check if task exists
            task = self.get(db, task_id)
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )
            
            # Access control for Tech Lead
            if current_user and current_user.role == "TECHNICAL_LEAD":
                # Check if tech lead is assigned to this batch (any TL position)
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, task.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete tasks in their assigned batches"
                    )
            
            # Call parent delete
            super().delete(db, task_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete task"
            )

    def _ensure_batch_exists(self, db: Session, batch_id: UUID) -> None:
        try:
            batch = db.get(Batch, batch_id)
            if batch is None:
                raise ConflictError(f"Batch '{batch_id}' does not exist.")
        except ConflictError:
            raise
        except Exception as e:
            logger.error(f"Error checking batch existence: {e}")
            raise ConflictError(f"Could not verify batch '{batch_id}'.")


task_service = TaskService()
