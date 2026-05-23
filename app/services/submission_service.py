from datetime import date
from uuid import UUID
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, or_, func

from app.models.batch import Batch
from app.models.submission import Submission
from app.models.profile import Profile
from app.schemas.submission import SubmissionCreate, SubmissionUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError

logger = logging.getLogger(__name__)


class SubmissionService(CRUDService[Submission]):
    model = Submission
    resource_name = "Submission"
    table_name = "submissions"

    def create_submission(self, db: Session, payload: SubmissionCreate) -> Submission:
        self._ensure_profile_exists(db, payload.user_id)
        duplicate = (
            db.query(Submission)
            .filter(
                Submission.user_id == payload.user_id,
                Submission.submitted_for == payload.submitted_for,
            )
            .first()
        )
        if duplicate is not None:
            raise ConflictError("Submission already exists for this user on the given date.")

        return self.create(
            db,
            {
                "user_id": payload.user_id,
                "submitted_for": payload.submitted_for,
                "content": payload.content.strip(),
            },
        )

    def list_submissions(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: UUID | None = None,
        submitted_for: date | None = None,
        search: str | None = None,
        batch_id: UUID | None = None,
        sort_by: str | None = None,
        order: str | None = None,
        current_user=None,
    ) -> list[Submission]:
        from sqlalchemy.orm import joinedload
        try:
            # Start with base query - use joinedload to avoid N+1 queries
            # Optimized to load only required columns from Profile and Batch
            query = (
                db.query(Submission)
                .options(
                    joinedload(Submission.profile).load_only(Profile.id, Profile.name, Profile.batch_id),
                    joinedload(Submission.profile).joinedload(Profile.batch).load_only(Batch.id, Batch.name)
                )
                .join(Profile, Submission.user_id == Profile.id)
                .outerjoin(Batch, Profile.batch_id == Batch.id)
            )
            
            # CRITICAL: RBAC enforcement for TECHNICAL_LEAD
            if current_user and current_user.role == "TECHNICAL_LEAD":
                # Tech Lead can only see submissions from interns in their assigned batches
                from app.core.tech_lead_utils import get_tech_lead_batch_ids
                tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
                if tl_batch_ids:
                    query = query.filter(Profile.batch_id.in_(tl_batch_ids))
                else:
                    # Tech lead has no batches assigned, show nothing
                    query = query.filter(Profile.id == None)
            
            # Filter by user_id
            if user_id:
                query = query.filter(Submission.user_id == user_id)
            
            # Filter by submitted_for date
            if submitted_for:
                query = query.filter(Submission.submitted_for == submitted_for)
            
            # Filter by batch_id
            if batch_id:
                query = query.filter(Profile.batch_id == batch_id)
            
            # Search across multiple fields
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                query = query.filter(
                    or_(
                        func.lower(Profile.name).like(search_term),
                        func.lower(Submission.content).like(search_term)
                    )
                )
            
            # Sorting
            VALID_SORT_FIELDS = {"submitted_for", "created_at", "content"}
            if sort_by and sort_by in VALID_SORT_FIELDS:
                order_func = desc if order and order.lower() == "desc" else asc
                if sort_by == "submitted_for":
                    query = query.order_by(order_func(Submission.submitted_for))
                elif sort_by == "created_at":
                    query = query.order_by(order_func(Submission.created_at))
                elif sort_by == "content":
                    query = query.order_by(order_func(Submission.content))
            else:
                # Default sorting
                query = query.order_by(Submission.submitted_for.desc(), Submission.created_at.desc())
            
            # Apply pagination
            submissions = query.offset(skip).limit(limit).all()
            
            # Populate helper attributes from already loaded relationships
            for sub in submissions:
                if sub.profile:
                    sub.submitted_by_name = sub.profile.name
                    sub.batch_id = sub.profile.batch_id
                    sub.batch_name = sub.profile.batch.name if sub.profile.batch else None
                else:
                    sub.submitted_by_name = None
                    sub.batch_id = None
                    sub.batch_name = None
            
            return submissions
        except Exception as e:
            logger.error(f"Error in list_submissions: {e}")
            return []

    def update_submission(self, db: Session, submission_id: UUID, payload: SubmissionUpdate, current_user) -> Submission:
        # Check access before update
        submission = self.get(db, submission_id)
        
        if current_user.role == "ADMIN":
            # Admin can update any submission
            pass
        elif current_user.role == "TECHNICAL_LEAD":
            # Tech Lead can update submissions from interns in their batches
            intern = db.get(Profile, submission.user_id)
            
            if intern.batch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update submission for intern not in any batch"
                )
            
            # MULTI-BATCH: Check if intern is in any batch where TL is assigned
            from app.core.tech_lead_utils import is_tech_lead_for_batch
            if not is_tech_lead_for_batch(db, current_user.id, intern.batch_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Lead can only update submissions from their assigned batches"
                )
        elif current_user.role == "INTERN":
            # Intern can only update their own submissions
            if submission.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own submissions"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized to update submissions"
            )
        
        return self.update(db, submission_id, {"content": payload.content.strip()})

    def delete(self, db: Session, submission_id: UUID, current_user=None) -> None:
        # Check access before delete
        if current_user:
            submission = self.get(db, submission_id)
            
            if current_user.role == "ADMIN":
                # Admin can delete any submission
                pass
            elif current_user.role == "TECHNICAL_LEAD":
                # Tech Lead can delete submissions from interns in their batches
                intern = db.get(Profile, submission.user_id)
                
                if intern.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot delete submission for intern not in any batch"
                    )
                
                # MULTI-BATCH: Check if intern is in any batch where TL is assigned
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, intern.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete submissions from their assigned batches"
                    )
            elif current_user.role == "INTERN":
                # Intern can only delete their own submissions
                if submission.user_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You can only delete your own submissions"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized to delete submissions"
                )
        
        # Call parent delete
        super().delete(db, submission_id)

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        if db.get(Profile, profile_id) is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")


submission_service = SubmissionService()
