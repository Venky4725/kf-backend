from uuid import UUID
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.batch import Batch
from app.models.evaluation import Evaluation
from app.models.profile import Profile
from app.schemas.evaluation import EvaluationCreate, EvaluationUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError, ValidationError

logger = logging.getLogger(__name__)


class EvaluationService(CRUDService[Evaluation]):
    model = Evaluation
    resource_name = "Evaluation"
    table_name = "evaluations"

    def create_evaluation(self, db: Session, payload: EvaluationCreate, current_user) -> Evaluation:
        intern = self._get_profile(db, payload.intern_id, "intern")
        reviewer = self._get_profile(db, payload.reviewed_by, "reviewer")

        if intern.role != "INTERN":
            raise ValidationError("Evaluation target must have role INTERN.")
        if reviewer.role not in {"TECHNICAL_LEAD", "ADMIN"}:
            raise ValidationError("Reviewer must have role TECHNICAL_LEAD or ADMIN.")
        if payload.week_number < 1:
            raise ValidationError("Week number must be greater than or equal to 1.")
        if payload.score < 0 or payload.score > 5:
            raise ValidationError("Score must be between 0 and 5.")
        
        # Tech Lead can only create evaluations for interns in their assigned batches
        if current_user.role == "TECHNICAL_LEAD":
            if intern.batch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot evaluate intern not assigned to any batch"
                )
            batch = db.get(Batch, intern.batch_id)
            if batch.team_lead_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Lead can only evaluate interns in their assigned batches"
                )

        return self.create(
            db,
            {
                "intern_id": payload.intern_id,
                "reviewed_by": payload.reviewed_by,
                "week_number": payload.week_number,
                "score": payload.score,
                "feedback": payload.feedback.strip() if payload.feedback else None,
            },
        )

    def list_evaluations(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        intern_id: UUID | None = None,
        reviewed_by: UUID | None = None,
        week_number: int | None = None,
        search: str | None = None,
        batch_id: UUID | None = None,
        sort_by: str | None = None,
        order: str | None = None,
    ) -> list[Evaluation]:
        from sqlalchemy import asc, desc
        
        try:
            # Start with base query - join with Profile for search on intern name
            query = db.query(Evaluation).join(Profile, Evaluation.intern_id == Profile.id)
            
            # Filter by intern_id
            if intern_id:
                query = query.filter(Evaluation.intern_id == intern_id)
            
            # Filter by reviewed_by
            if reviewed_by:
                query = query.filter(Evaluation.reviewed_by == reviewed_by)
            
            # Filter by week_number (NEW)
            if week_number is not None:
                query = query.filter(Evaluation.week_number == week_number)
            
            # Filter by batch_id
            if batch_id:
                query = query.filter(Profile.batch_id == batch_id)
            
            # Search across multiple fields (intern name and feedback)
            # IMPORTANT: Use LIKE '%search%' for partial matching
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                try:
                    # Search in intern name and feedback
                    search_conditions = [func.lower(Profile.name).like(search_term)]
                    
                    # Only search feedback if it's not NULL
                    search_conditions.append(func.lower(Evaluation.feedback).like(search_term))
                    
                    query = query.filter(or_(*search_conditions))
                except Exception as e:
                    logger.error(f"Error applying search filter: {e}")
                    # Continue without search filter
            
            # Sorting
            VALID_SORT_FIELDS = {"week_number", "score", "created_at"}
            if sort_by and sort_by in VALID_SORT_FIELDS:
                try:
                    order_func = desc if order and order.lower() == "desc" else asc
                    if sort_by == "week_number":
                        query = query.order_by(order_func(Evaluation.week_number))
                    elif sort_by == "score":
                        query = query.order_by(order_func(Evaluation.score))
                    elif sort_by == "created_at":
                        query = query.order_by(order_func(Evaluation.created_at))
                except Exception as e:
                    logger.error(f"Error applying sort: {e}")
                    # Continue with default sorting
                    query = query.order_by(Evaluation.week_number.desc(), Evaluation.created_at.desc())
            else:
                # Default sorting
                query = query.order_by(Evaluation.week_number.desc(), Evaluation.created_at.desc())
            
            # Apply pagination
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error in list_evaluations: {e}")
            # Return empty list instead of crashing
            return []

    def update_evaluation(self, db: Session, evaluation_id: UUID, payload: EvaluationUpdate, current_user) -> Evaluation:
        # Check access before update
        evaluation = self.get(db, evaluation_id)
        
        if current_user.role == "TECHNICAL_LEAD":
            intern = db.get(Profile, evaluation.intern_id)
            if intern.batch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update evaluation for intern not in any batch"
                )
            batch = db.get(Batch, intern.batch_id)
            if batch.team_lead_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Lead can only update evaluations in their assigned batches"
                )
        
        updates = payload.model_dump(exclude_unset=True)
        if "score" in updates and updates["score"] is not None and (updates["score"] < 0 or updates["score"] > 5):
            raise ValidationError("Score must be between 0 and 5.")
        if "feedback" in updates and updates["feedback"] is not None:
            updates["feedback"] = updates["feedback"].strip()
        return self.update(db, evaluation_id, updates)

    def delete(self, db: Session, evaluation_id: UUID, current_user=None) -> None:
        # Check access before delete
        if current_user:
            evaluation = self.get(db, evaluation_id)
            
            if current_user.role == "TECHNICAL_LEAD":
                intern = db.get(Profile, evaluation.intern_id)
                if intern.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot delete evaluation for intern not in any batch"
                    )
                batch = db.get(Batch, intern.batch_id)
                if batch.team_lead_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete evaluations in their assigned batches"
                    )
        
        # Call parent delete
        super().delete(db, evaluation_id)

    def _get_profile(self, db: Session, profile_id: UUID, label: str) -> Profile:
        profile = db.get(Profile, profile_id)
        if profile is None:
            raise ConflictError(f"{label.capitalize()} profile '{profile_id}' does not exist.")
        return profile


evaluation_service = EvaluationService()
