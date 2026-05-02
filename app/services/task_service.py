from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError


class TaskService(CRUDService[Task]):
    model = Task
    resource_name = "Task"
    table_name = "tasks"

    def create_task(self, db: Session, payload: TaskCreate) -> Task:
        self._ensure_batch_exists(db, payload.batch_id)
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

    def update_task(self, db: Session, task_id: UUID, payload: TaskUpdate) -> Task:
        updates = payload.model_dump(exclude_unset=True)
        if "title" in updates and updates["title"] is not None:
            updates["title"] = updates["title"].strip()
        return self.update(db, task_id, updates)

    def _ensure_batch_exists(self, db: Session, batch_id: UUID) -> None:
        from app.models.batch import Batch

        if db.get(Batch, batch_id) is None:
            raise ConflictError(f"Batch '{batch_id}' does not exist.")


task_service = TaskService()
