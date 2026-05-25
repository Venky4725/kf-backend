from uuid import UUID
import logging
from datetime import datetime, date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import asc, desc
from sqlalchemy.exc import SQLAlchemyError

from app.models.batch import Batch
from app.models.profile import Profile
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskBulkCreate, TaskBulkResponse
from app.services.base import CRUDService
from app.services.exceptions import ConflictError
from app.utils.task_parser import parse_simple_tasks, parse_roadmap_tasks

logger = logging.getLogger(__name__)


class TaskService(CRUDService[Task]):
    model = Task
    resource_name = "Task"
    table_name = "tasks"

    def get(self, db: Session, task_id: UUID) -> Task:
        """Get single task with enriched batch_name and assigned_to_name"""
        from app.services.exceptions import NotFoundError
        task = db.query(Task).options(selectinload(Task.weekly_plan_days)).filter(Task.id == task_id).first()
        if not task:
            raise NotFoundError(self.resource_name, str(task_id))
        
        # Enrich with batch_name and assigned_to_name
        try:
            if task.batch_id:
                batch = db.get(Batch, task.batch_id)
                task.batch_name = batch.name if batch else None
            else:
                task.batch_name = None
            
            if hasattr(task, 'assigned_to') and task.assigned_to:
                assignee = db.get(Profile, task.assigned_to)
                task.assigned_to_name = assignee.name if assignee else None
            else:
                task.assigned_to_name = None
        except Exception as e:
            logger.error(f"Error enriching task {task_id}: {e}")
            task.batch_name = None
            task.assigned_to_name = None
        
        return task

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
                "priority": payload.priority or "MEDIUM",
                "status": payload.status or "OPEN",
                "created_by": current_user.id if current_user else None,
                "task_type": payload.task_type,
                "roadmap_entries": [e.model_dump() for e in payload.roadmap_entries] if payload.roadmap_entries else None,
                "role": payload.role
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

    def create_tasks_bulk(self, db: Session, payload: TaskBulkCreate, current_user) -> TaskBulkResponse:
        """Create multiple tasks in a single transaction."""
        try:
            # 1. Common Validations
            self._ensure_batch_exists(db, payload.batch_id)
            
            # Tech Lead permission check
            if current_user.role == "TECHNICAL_LEAD":
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, payload.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only create tasks for their assigned batches"
                    )
            
            # Validate assigned_to user exists
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

            # 2. Process Task List (Legacy, Smart Import, or Structured Roadmap)
            tasks_to_create = []
            import_mode = payload.import_mode or "legacy"
            
            # Add logging as requested
            print(f"DEBUG: Bulk task creation payload: {payload.model_dump()}")
            
            if payload.task_type == "roadmap" and payload.roadmap_entries:
                import_mode = "structured_roadmap"
                # Create ONE task for the entire roadmap
                first_topic = payload.roadmap_entries[0].topic if payload.roadmap_entries else "Training Roadmap"
                tasks_to_create.append({
                    "title": f"Roadmap: {first_topic}",
                    "description": "Weekly Training Roadmap (see structured entries)",
                    "task_type": "roadmap",
                    "roadmap_entries": [e.model_dump() for e in payload.roadmap_entries],
                    "due_date": payload.due_date,
                    "role": payload.role
                })
            elif payload.tasks:
                import_mode = "tasks_list"
                from app.schemas.task import RoadmapTask
                roadmap_items = [item for item in payload.tasks if isinstance(item, RoadmapTask)]
                legacy_items = [item for item in payload.tasks if isinstance(item, str)]
                
                if roadmap_items:
                    # Create ONE task for the entire roadmap
                    first_topic = roadmap_items[0].topic
                    tasks_to_create.append({
                        "title": f"Roadmap: {first_topic}",
                        "description": "Weekly Training Roadmap (see structured entries)",
                        "task_type": "roadmap",
                        "roadmap_entries": [item.model_dump() for item in roadmap_items],
                        "due_date": payload.due_date,
                        "role": payload.role
                    })
                
                # Still handle legacy string titles (these remain separate tasks)
                for item in legacy_items:
                    if item.strip():
                        tasks_to_create.append({
                            "title": item.strip(),
                            "description": None,
                            "due_date": payload.due_date,
                            "role": payload.role
                        })
            elif payload.import_mode:
                if payload.import_mode == "simple":
                    tasks_to_create = parse_simple_tasks(payload.content)
                elif payload.import_mode == "roadmap":
                    tasks_to_create = parse_roadmap_tasks(payload.content)

            if not tasks_to_create:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No valid tasks found to import"
                )

            created_tasks = []
            task_ids = []
            
            # Use manual transaction/flush to handle batching
            try:
                for task_data in tasks_to_create:
                    task = Task(
                        title=task_data["title"],
                        description=task_data.get("description"),
                        batch_id=payload.batch_id,
                        due_date=task_data.get("due_date"),
                        priority="LOW",
                        status="PENDING",
                        assigned_to=payload.assigned_to,
                        created_by=current_user.id if current_user else None,
                        task_type=task_data.get("task_type"),
                        roadmap_entries=task_data.get("roadmap_entries"),
                        role=task_data.get("role")
                    )
                    db.add(task)
                    created_tasks.append(task)
                
                db.flush() # Ensure IDs are generated
                
                for task in created_tasks:
                    task_ids.append(task.id)
                    # Add audit log for each
                    from app.services.audit import add_audit_log
                    add_audit_log(db, action="CREATE", table_name=self.table_name, record_id=task.id)
                
                db.commit()
                
                logger.info(
                    f"Smart Bulk Import (mode={import_mode}) created {len(task_ids)} tasks "
                    f"for batch {payload.batch_id} by {current_user.id if current_user else 'unknown'}"
                )
                
                return TaskBulkResponse(
                    created=len(task_ids),
                    failed=0,
                    task_ids=task_ids
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Error in bulk task creation transaction: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create tasks: {str(e)}"
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in bulk task creation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unexpected error during bulk task creation"
            )

    def list_tasks(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        batch_id: UUID | None = None,
        role: str | None = None,
        search: str | None = None,
        due_date: date | None = None,
        sort_by: str | None = None,
        order: str | None = None,
        current_user = None
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
            
            # Filter by role
            if role:
                query = query.filter(Task.role == role)
            
            # Filter by due_date (actual assigned date)
            if due_date:
                query = query.filter(Task.due_date == due_date)
            
            # Role-based filtering for Interns
            if current_user and current_user.role == "INTERN":
                from sqlalchemy import or_
                # Interns only see:
                # 1. Tasks assigned to them specifically
                # 2. Tasks assigned to their intern_role (AIML, Full Stack)
                # 3. Tasks assigned to the whole batch (no specific user or role)
                query = query.filter(
                    or_(
                        Task.assigned_to == current_user.id,
                        Task.role == current_user.intern_role,
                        (Task.assigned_to == None) & (Task.role == None)
                    )
                )

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
                tasks = query.offset(skip).limit(limit).all()
                
                # Enrich with batch_name and assigned_to_name
                for task in tasks:
                    try:
                        # Get batch name
                        if task.batch_id:
                            batch = db.get(Batch, task.batch_id)
                            task.batch_name = batch.name if batch else None
                        else:
                            task.batch_name = None
                        
                        # Get assigned_to name
                        if hasattr(task, 'assigned_to') and task.assigned_to:
                            assignee = db.get(Profile, task.assigned_to)
                            task.assigned_to_name = assignee.name if assignee else None
                        else:
                            task.assigned_to_name = None
                    except Exception as e:
                        logger.error(f"Error enriching task {task.id}: {e}")
                        task.batch_name = None
                        task.assigned_to_name = None
                
                return tasks if tasks else []
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
