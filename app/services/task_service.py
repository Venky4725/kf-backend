from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError


class TaskService(CRUDService[Task]):
    model = Task
    resource_name = "Task"
    table_name = "tasks"

    def create_task(self, db: Session, payload: TaskCreate, current_user) -> Task:
        self._ensure_batch_exists(db, payload.batch_id)
        
        # Tech Lead can only create tasks for their assigned batches
        if current_user.role == "TECHNICAL_LEAD":
            batch = db.get(Batch, payload.batch_id)
            if batch.team_lead_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Lead can only create tasks for their assigned batches"
                )
        
        return self.create(
            db,
            {
                "title": payload.title.strip(),
                "description": payload.description,
                "batch_id": payload.batch_id,
                "due_date": payload.due_date,
            },
        )

    def list_tasks(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        batch_id: UUID | None = None,
    ) -> list[Task]:
        query = db.query(Task)
        if batch_id:
            query = query.filter(Task.batch_id == batch_id)
        return query.order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.created_at.desc()).offset(skip).limit(limit).all()

    def update_task(self, db: Session, task_id: UUID, payload: TaskUpdate, current_user) -> Task:
        # Check access before update
        task = self.get(db, task_id)
        
        if current_user.role == "TECHNICAL_LEAD":
            batch = db.get(Batch, task.batch_id)
            if batch.team_lead_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Lead can only update tasks in their assigned batches"
                )
        
        updates = payload.model_dump(exclude_unset=True)
        if "title" in updates and updates["title"] is not None:
            updates["title"] = updates["title"].strip()
        return self.update(db, task_id, updates)

    def delete(self, db: Session, task_id: UUID, current_user=None) -> None:
        # Check access before delete
        if current_user:
            task = self.get(db, task_id)
            
            if current_user.role == "TECHNICAL_LEAD":
                batch = db.get(Batch, task.batch_id)
                if batch.team_lead_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete tasks in their assigned batches"
                    )
        
        # Call parent delete
        super().delete(db, task_id)

    def _ensure_batch_exists(self, db: Session, batch_id: UUID) -> None:
        if db.get(Batch, batch_id) is None:
            raise ConflictError(f"Batch '{batch_id}' does not exist.")


task_service = TaskService()
