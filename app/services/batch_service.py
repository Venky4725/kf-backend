from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.profile import Profile
from app.models.task import Task
from app.schemas.batch import BatchCreate, BatchUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError, ValidationError


class BatchService(CRUDService[Batch]):
    model = Batch
    resource_name = "Batch"
    table_name = "batches"

    def create_batch(self, db: Session, payload: BatchCreate) -> Batch:
        if payload.team_lead_id is not None:
            self._ensure_team_lead(db, payload.team_lead_id)

        return self.create(
            db,
            {
                "name": payload.name.strip(),
                "tech_stack": payload.tech_stack.strip(),
                "start_date": payload.start_date,
                "team_lead_id": payload.team_lead_id,
            },
        )

    def list_batches(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        team_lead_id: UUID | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        order: str | None = None,
    ) -> list[Batch]:
        from sqlalchemy import asc, desc
        
        query = db.query(Batch)
        
        if team_lead_id:
            # Find batches where:
            # 1. team_lead_id matches (batch assigned TO the TL), OR
            # 2. The TL's profile.batch_id matches the batch (TL belongs to the batch)
            tl_profile = db.query(Profile).filter(Profile.id == team_lead_id).first()
            
            if tl_profile and tl_profile.batch_id:
                # TL has a batch_id, so include both relationships
                query = query.filter(
                    (Batch.team_lead_id == team_lead_id) | (Batch.id == tl_profile.batch_id)
                )
            else:
                # TL has no batch_id, only check team_lead_id
                query = query.filter(Batch.team_lead_id == team_lead_id)
        
        # Search in name and tech_stack
        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                (Batch.name.ilike(search_pattern)) |
                (Batch.tech_stack.ilike(search_pattern))
            )
        
        # Sorting
        VALID_SORT_FIELDS = {"name", "tech_stack", "start_date", "created_at"}
        if sort_by and sort_by in VALID_SORT_FIELDS:
            order_func = desc if order and order.lower() == "desc" else asc
            if sort_by == "name":
                query = query.order_by(order_func(Batch.name))
            elif sort_by == "tech_stack":
                query = query.order_by(order_func(Batch.tech_stack))
            elif sort_by == "start_date":
                query = query.order_by(order_func(Batch.start_date))
            elif sort_by == "created_at":
                query = query.order_by(order_func(Batch.created_at))
        else:
            # Default sorting
            query = query.order_by(Batch.start_date.desc(), Batch.created_at.desc())
        
        return query.offset(skip).limit(limit).all()

    def update_batch(self, db: Session, batch_id: UUID, payload: BatchUpdate) -> Batch:
        updates = payload.model_dump(exclude_unset=True)
        if "team_lead_id" in updates and updates["team_lead_id"] is not None:
            self._ensure_team_lead(db, updates["team_lead_id"])
        if "name" in updates and updates["name"] is not None:
            updates["name"] = updates["name"].strip()
        if "tech_stack" in updates and updates["tech_stack"] is not None:
            updates["tech_stack"] = updates["tech_stack"].strip()
        return self.update(db, batch_id, updates)

    def delete(self, db: Session, batch_id: UUID) -> None:
        """
        Delete a batch with automatic cleanup of dependencies.
        
        This method will:
        1. Unassign all profiles from the batch (set batch_id to NULL)
        2. Unassign all tasks from the batch (set batch_id to NULL)
        3. Delete the batch record
        
        This ensures clean deletion even if the assigned tech lead is deactivated.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the batch first to ensure it exists
        batch = self.get(db, batch_id)
        logger.info(f"Deleting batch: {batch.name} (ID: {batch_id})")
        
        # Step 1: Unassign all profiles from this batch
        profile_count = db.query(Profile).filter(Profile.batch_id == batch_id).count()
        if profile_count > 0:
            logger.info(f"Unassigning {profile_count} profile(s) from batch")
            db.query(Profile).filter(Profile.batch_id == batch_id).update(
                {"batch_id": None},
                synchronize_session=False
            )
            db.flush()
        
        # Step 2: Unassign all tasks from this batch
        task_count = db.query(Task).filter(Task.batch_id == batch_id).count()
        if task_count > 0:
            logger.info(f"Unassigning {task_count} task(s) from batch")
            db.query(Task).filter(Task.batch_id == batch_id).update(
                {"batch_id": None},
                synchronize_session=False
            )
            db.flush()
        
        # Step 3: Add audit log
        try:
            from app.services.audit import add_audit_log
            add_audit_log(db, action="DELETE", table_name=self.table_name, record_id=batch_id)
        except Exception as e:
            logger.warning(f"Could not add audit log: {e}")
        
        # Step 4: Delete the batch
        db.delete(batch)
        self._commit(db)
        
        logger.info(f"Successfully deleted batch: {batch.name} (unassigned {profile_count} profiles, {task_count} tasks)")

    def _ensure_team_lead(self, db: Session, team_lead_id: UUID) -> None:
        profile = db.get(Profile, team_lead_id)
        if profile is None:
            raise ConflictError(f"Profile '{team_lead_id}' does not exist.")
        if profile.role != "TECHNICAL_LEAD":
            raise ValidationError("Assigned team lead must have role TECHNICAL_LEAD.")
        if not profile.is_active:
            raise ValidationError("Cannot assign inactive tech lead to batch.")


batch_service = BatchService()
