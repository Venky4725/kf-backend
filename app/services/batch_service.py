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
    ) -> list[Batch]:
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
        
        return query.order_by(Batch.start_date.desc(), Batch.created_at.desc()).offset(skip).limit(limit).all()

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
        # Check for dependent profiles
        profile_count = db.query(Profile).filter(Profile.batch_id == batch_id).count()
        task_count = db.query(Task).filter(Task.batch_id == batch_id).count()

        dependent_records = []
        if profile_count > 0:
            dependent_records.append(f"{profile_count} profile(s)")
        if task_count > 0:
            dependent_records.append(f"{task_count} task(s)")

        if dependent_records:
            raise ConflictError(
                f"Cannot delete batch: has {', '.join(dependent_records)}. "
                f"Remove or reassign these records first."
            )

        # Also check if batch has a team lead assigned
        batch = self.get(db, batch_id)
        if batch and batch.team_lead_id is not None:
            # Optionally warn or prevent - for now we allow deletion if no other dependents
            pass

        # Proceed with deletion
        instance = self.get(db, batch_id)
        from app.services.audit import add_audit_log
        add_audit_log(db, action="DELETE", table_name=self.table_name, record_id=batch_id)
        db.delete(instance)
        self._commit(db)

    def _ensure_team_lead(self, db: Session, team_lead_id: UUID) -> None:
        profile = db.get(Profile, team_lead_id)
        if profile is None:
            raise ConflictError(f"Profile '{team_lead_id}' does not exist.")
        if profile.role != "TECHNICAL_LEAD":
            raise ValidationError("Assigned team lead must have role TECHNICAL_LEAD.")
        if not profile.is_active:
            raise ValidationError("Cannot assign inactive tech lead to batch.")


batch_service = BatchService()
