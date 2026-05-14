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
    ) -> list[Submission]:
        try:
            # Start with base query - join with Profile and Batch for complete data
            query = (
                db.query(Submission)
                .join(Profile, Submission.user_id == Profile.id)
                .outerjoin(Batch, Profile.batch_id == Batch.id)  # LEFT JOIN for batch
            )
            
            # Filter by user_id
            if user_id:
                query = query.filter(Submission.user_id == user_id)
            
            # Filter by submitted_for date
            if submitted_for:
                query = query.filter(Submission.submitted_for == submitted_for)
            
            # Filter by batch_id
            if batch_id:
                query = query.filter(Profile.batch_id == batch_id)
            
            # Search across multiple fields (intern name and content)
            # IMPORTANT: Use LIKE '%search%' for partial matching, not just 'search%'
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                try:
                    query = query.filter(
                        or_(
                            func.lower(Profile.name).like(search_term),
                            func.lower(Submission.content).like(search_term)
                        )
                    )
                except Exception as e:
                    logger.error(f"Error applying search filter: {e}")
                    # Continue without search filter
            
            # Sorting
            VALID_SORT_FIELDS = {"submitted_for", "created_at", "content"}
            if sort_by and sort_by in VALID_SORT_FIELDS:
                try:
                    order_func = desc if order and order.lower() == "desc" else asc
                    if sort_by == "submitted_for":
                        query = query.order_by(order_func(Submission.submitted_for))
                    elif sort_by == "created_at":
                        query = query.order_by(order_func(Submission.created_at))
                    elif sort_by == "content":
                        query = query.order_by(order_func(Submission.content))
                except Exception as e:
                    logger.error(f"Error applying sort: {e}")
                    # Continue with default sorting
                    query = query.order_by(Submission.submitted_for.desc(), Submission.created_at.desc())
            else:
                # Default sorting
                query = query.order_by(Submission.submitted_for.desc(), Submission.created_at.desc())
            
            # Apply pagination
            submissions = query.offset(skip).limit(limit).all()
            
            # Add submitted_by_name, batch_id, and batch_name from joined data
            result = []
            for sub in submissions:
                try:
                    # Get profile and batch info
                    profile = db.query(Profile).filter(Profile.id == sub.user_id).first()
                    if profile:
                        sub.submitted_by_name = profile.name
                        sub.batch_id = profile.batch_id
                        # Get batch name if profile has batch
                        if profile.batch_id:
                            batch = db.get(Batch, profile.batch_id)
                            sub.batch_name = batch.name if batch else None
                        else:
                            sub.batch_name = None
                    else:
                        sub.submitted_by_name = None
                        sub.batch_id = None
                        sub.batch_name = None
                except Exception as e:
                    logger.error(f"Error fetching profile/batch for submission: {e}")
                    sub.submitted_by_name = None
                    sub.batch_id = None
                    sub.batch_name = None
                result.append(sub)
            
            return result
        except Exception as e:
            logger.error(f"Error in list_submissions: {e}")
            # Return empty list instead of crashing
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
