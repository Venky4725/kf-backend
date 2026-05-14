from uuid import UUID

from sqlalchemy import func, or_
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
        # Validate first tech lead
        if payload.first_tech_lead_id is not None:
            self._ensure_tech_lead(db, payload.first_tech_lead_id, "first")
        
        # Validate second tech lead
        if payload.second_tech_lead_id is not None:
            self._ensure_tech_lead(db, payload.second_tech_lead_id, "second")
        
        # Ensure they are different (additional server-side check)
        if (payload.first_tech_lead_id is not None and 
            payload.second_tech_lead_id is not None and 
            payload.first_tech_lead_id == payload.second_tech_lead_id):
            raise ValidationError("First and second tech leads must be different.")

        return self.create(
            db,
            {
                "name": payload.name.strip(),
                "tech_stack": payload.tech_stack.strip(),
                "start_date": payload.start_date,
                "first_tech_lead_id": payload.first_tech_lead_id,
                "second_tech_lead_id": payload.second_tech_lead_id,
            },
        )

    def _enrich_batch_response(self, db: Session, batch: Batch) -> dict:
        """
        Enrich a single batch with tech lead information.
        This ensures consistent response structure across all batch endpoints.
        """
        batch_dict = {
            "id": batch.id,
            "name": batch.name,
            "tech_stack": batch.tech_stack,
            "start_date": batch.start_date,
            "first_tech_lead_id": batch.first_tech_lead_id,
            "second_tech_lead_id": batch.second_tech_lead_id,
            "created_at": batch.created_at,
            "updated_at": batch.updated_at,
            "first_tech_lead": None,
            "second_tech_lead": None,
            "tech_leads_display": "Unassigned"
        }
        
        # Get first tech lead info
        if batch.first_tech_lead_id:
            first_tl = db.get(Profile, batch.first_tech_lead_id)
            if first_tl:
                batch_dict["first_tech_lead"] = {
                    "id": first_tl.id,
                    "name": first_tl.name,
                    "email": first_tl.email
                }
        
        # Get second tech lead info
        if batch.second_tech_lead_id:
            second_tl = db.get(Profile, batch.second_tech_lead_id)
            if second_tl:
                batch_dict["second_tech_lead"] = {
                    "id": second_tl.id,
                    "name": second_tl.name,
                    "email": second_tl.email
                }
        
        # Build display string
        first_name = batch_dict["first_tech_lead"]["name"] if batch_dict["first_tech_lead"] else None
        second_name = batch_dict["second_tech_lead"]["name"] if batch_dict["second_tech_lead"] else None
        
        if first_name and second_name:
            batch_dict["tech_leads_display"] = f"{first_name}/{second_name}"
        elif first_name:
            batch_dict["tech_leads_display"] = first_name
        elif second_name:
            batch_dict["tech_leads_display"] = second_name
        else:
            batch_dict["tech_leads_display"] = "Unassigned"
        
        return batch_dict

    def list_batches(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        tech_lead_id: UUID | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        order: str | None = None,
    ) -> list[dict]:
        """
        List batches with optional filtering by tech lead.
        Returns enriched batch data with tech lead names.
        
        If tech_lead_id is provided, returns batches where the tech lead is assigned
        as either first_tech_lead_id OR second_tech_lead_id.
        """
        from sqlalchemy import asc, desc
        
        query = db.query(Batch)
        
        if tech_lead_id:
            # Find batches where tech lead is assigned as first OR second tech lead
            tl_profile = db.query(Profile).filter(Profile.id == tech_lead_id).first()
            
            if tl_profile and tl_profile.batch_id:
                # TL has a batch_id, so include:
                # 1. Batches where TL is first_tech_lead_id
                # 2. Batches where TL is second_tech_lead_id
                # 3. Batch that TL belongs to (profile.batch_id)
                query = query.filter(
                    or_(
                        Batch.first_tech_lead_id == tech_lead_id,
                        Batch.second_tech_lead_id == tech_lead_id,
                        Batch.id == tl_profile.batch_id
                    )
                )
            else:
                # TL has no batch_id, check first_tech_lead_id OR second_tech_lead_id
                query = query.filter(
                    or_(
                        Batch.first_tech_lead_id == tech_lead_id,
                        Batch.second_tech_lead_id == tech_lead_id
                    )
                )
        
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
        
        batches = query.offset(skip).limit(limit).all()
        
        # Enrich with tech lead information using the helper method
        return [self._enrich_batch_response(db, batch) for batch in batches]

    def update_batch(self, db: Session, batch_id: UUID, payload: BatchUpdate) -> Batch:
        updates = payload.model_dump(exclude_unset=True)
        
        # Validate first tech lead if being updated
        if "first_tech_lead_id" in updates and updates["first_tech_lead_id"] is not None:
            self._ensure_tech_lead(db, updates["first_tech_lead_id"], "first")
        
        # Validate second tech lead if being updated
        if "second_tech_lead_id" in updates and updates["second_tech_lead_id"] is not None:
            self._ensure_tech_lead(db, updates["second_tech_lead_id"], "second")
        
        # Ensure they are different (if both are being set)
        first_tl = updates.get("first_tech_lead_id")
        second_tl = updates.get("second_tech_lead_id")
        
        # If both are in the update and both are not None, check they're different
        if (first_tl is not None and second_tl is not None and first_tl == second_tl):
            raise ValidationError("First and second tech leads must be different.")
        
        # If only one is being updated, check against the existing value
        if first_tl is not None and "second_tech_lead_id" not in updates:
            # Check against existing second_tech_lead_id
            batch = self.get(db, batch_id)
            if batch.second_tech_lead_id is not None and first_tl == batch.second_tech_lead_id:
                raise ValidationError("First and second tech leads must be different.")
        
        if second_tl is not None and "first_tech_lead_id" not in updates:
            # Check against existing first_tech_lead_id
            batch = self.get(db, batch_id)
            if batch.first_tech_lead_id is not None and second_tl == batch.first_tech_lead_id:
                raise ValidationError("First and second tech leads must be different.")
        
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
        
        This ensures clean deletion even if the assigned tech leads are deactivated.
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

    def _ensure_tech_lead(self, db: Session, tech_lead_id: UUID, position: str = "") -> None:
        """
        Validate that a tech lead exists, has the correct role, and is active.
        
        Args:
            db: Database session
            tech_lead_id: UUID of the tech lead to validate
            position: "first" or "second" for better error messages
        """
        profile = db.get(Profile, tech_lead_id)
        position_str = f"{position} " if position else ""
        
        if profile is None:
            raise ConflictError(f"Profile '{tech_lead_id}' does not exist.")
        if profile.role != "TECHNICAL_LEAD":
            raise ValidationError(f"Assigned {position_str}tech lead must have role TECHNICAL_LEAD.")
        if not profile.is_active:
            raise ValidationError(f"Cannot assign inactive {position_str}tech lead to batch.")


batch_service = BatchService()
