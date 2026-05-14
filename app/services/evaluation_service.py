from uuid import UUID
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.batch import Batch
from app.models.evaluation import Evaluation
from app.models.profile import Profile
from app.schemas.evaluation import EvaluationCreate, EvaluationUpdate, EvaluationUpdateTechLead, EvaluationUpdateAdmin
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
            # Check if intern is in any batch where TL is assigned
            if intern.batch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot evaluate intern not assigned to any batch"
                )
            
            # Check if TL is assigned to intern's batch (any TL position)
            from app.core.tech_lead_utils import is_tech_lead_for_batch
            if not is_tech_lead_for_batch(db, current_user.id, intern.batch_id):
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
        current_user=None,
        skip: int = 0,
        limit: int = 100,
        intern_id: UUID | None = None,
        reviewed_by: UUID | None = None,
        week_number: int | None = None,
        search: str | None = None,
        batch_id: UUID | None = None,
        sort_by: str | None = None,
        order: str | None = None,
        score_min: float | None = None,
        score_max: float | None = None,
    ) -> list[Evaluation]:
        """
        List evaluations with comprehensive filtering, searching, and sorting.
        
        RBAC Enforcement:
        - ADMIN: Can see all evaluations
        - TECHNICAL_LEAD: Can only see evaluations for interns in their assigned batches
        - INTERN: Can see their own evaluations (handled at router level)
        """
        from sqlalchemy import asc, desc
        
        try:
            # Start with base query - join with Profile for search on intern name
            # Also join with Batch for TECHNICAL_LEAD filtering
            query = db.query(Evaluation).join(
                Profile, Evaluation.intern_id == Profile.id
            ).outerjoin(
                Batch, Profile.batch_id == Batch.id
            )
            
            # CRITICAL: RBAC enforcement for TECHNICAL_LEAD
            if current_user and current_user.role == "TECHNICAL_LEAD":
                # Tech Lead can only see evaluations for interns in their assigned batches
                from app.core.tech_lead_utils import get_tech_lead_batch_ids
                tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
                if tl_batch_ids:
                    query = query.filter(Profile.batch_id.in_(tl_batch_ids))
                    logger.info(f"Tech Lead filter applied: batch_ids={tl_batch_ids}")
                else:
                    # Tech lead has no batches assigned, show nothing
                    query = query.filter(Profile.id == None)
                    logger.info("Tech Lead has no assigned batches, showing no evaluations")
            
            # Filter by intern_id
            if intern_id:
                query = query.filter(Evaluation.intern_id == intern_id)
            
            # Filter by reviewed_by
            if reviewed_by:
                query = query.filter(Evaluation.reviewed_by == reviewed_by)
            
            # Filter by week_number
            if week_number is not None:
                query = query.filter(Evaluation.week_number == week_number)
            
            # Filter by batch_id
            if batch_id:
                query = query.filter(Profile.batch_id == batch_id)
            
            # Filter by score range
            if score_min is not None:
                # Validate score_min
                if score_min < 0 or score_min > 5:
                    logger.warning(f"Invalid score_min: {score_min}, ignoring filter")
                else:
                    query = query.filter(Evaluation.score >= score_min)
            
            if score_max is not None:
                # Validate score_max
                if score_max < 0 or score_max > 5:
                    logger.warning(f"Invalid score_max: {score_max}, ignoring filter")
                else:
                    query = query.filter(Evaluation.score <= score_max)
            
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
            VALID_SORT_FIELDS = {"week_number", "score", "created_at", "updated_at", "intern_name"}
            if sort_by and sort_by in VALID_SORT_FIELDS:
                try:
                    order_func = desc if order and order.lower() == "desc" else asc
                    if sort_by == "week_number":
                        query = query.order_by(order_func(Evaluation.week_number))
                    elif sort_by == "score":
                        query = query.order_by(order_func(Evaluation.score))
                    elif sort_by == "created_at":
                        query = query.order_by(order_func(Evaluation.created_at))
                    elif sort_by == "updated_at":
                        query = query.order_by(order_func(Evaluation.updated_at))
                    elif sort_by == "intern_name":
                        query = query.order_by(order_func(Profile.name))
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

    def update_evaluation(
        self, 
        db: Session, 
        evaluation_id: UUID, 
        payload: EvaluationUpdate | EvaluationUpdateTechLead | EvaluationUpdateAdmin, 
        current_user
    ) -> Evaluation:
        """
        Update evaluation with role-based field restrictions.
        
        ADMIN: Can update all fields (week_number, score, feedback, intern_id, reviewed_by)
        TECHNICAL_LEAD: Can only update week_number, score, feedback for evaluations in their assigned batches
        """
        # Check access before update
        evaluation = self.get(db, evaluation_id)
        
        if current_user.role == "TECHNICAL_LEAD":
            # Tech Lead can only update evaluations in their assigned batches
            intern = db.get(Profile, evaluation.intern_id)
            if intern is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Intern profile not found"
                )
            
            # Check if intern is in any batch where TL is assigned
            if intern.batch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update evaluation for intern not in any batch"
                )
            
            # Check if TL is assigned to intern's batch (any TL position)
            from app.core.tech_lead_utils import is_tech_lead_for_batch
            if not is_tech_lead_for_batch(db, current_user.id, intern.batch_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Lead can only update evaluations for interns in their assigned batches"
                )
            
            # CRITICAL: Tech Lead cannot change intern_id or reviewed_by
            # This is enforced at schema level (EvaluationUpdateTechLead) but double-check here
            updates = payload.model_dump(exclude_unset=True)
            if "intern_id" in updates or "reviewed_by" in updates:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Leads cannot change the intern or reviewer of an evaluation"
                )
        elif current_user.role == "ADMIN":
            # Admin has full access
            updates = payload.model_dump(exclude_unset=True)
        else:
            # Other roles not allowed
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update evaluations"
            )
        
        # Sanitize feedback
        if "feedback" in updates and updates["feedback"] is not None:
            updates["feedback"] = updates["feedback"].strip()
            
        # Validate intern_id if being changed (ADMIN only)
        if "intern_id" in updates and updates["intern_id"]:
            intern = self._get_profile(db, updates["intern_id"], "intern")
            if intern.role != "INTERN":
                raise ValidationError("Evaluation target must have role INTERN.")
                
        # Validate reviewed_by if being changed (ADMIN only)
        if "reviewed_by" in updates and updates["reviewed_by"]:
            reviewer = self._get_profile(db, updates["reviewed_by"], "reviewer")
            if reviewer.role not in {"TECHNICAL_LEAD", "ADMIN"}:
                raise ValidationError("Reviewer must have role TECHNICAL_LEAD or ADMIN.")

        return self.update(db, evaluation_id, updates)

    def delete(self, db: Session, evaluation_id: UUID, current_user=None) -> None:
        """
        Delete evaluation with role-based authorization.
        
        ADMIN: Can delete any evaluation
        TECHNICAL_LEAD: Can only delete evaluations for interns in their assigned batches
        """
        # Check access before delete
        if current_user:
            evaluation = self.get(db, evaluation_id)
            
            if current_user.role == "TECHNICAL_LEAD":
                # Tech Lead can only delete evaluations in their assigned batches
                intern = db.get(Profile, evaluation.intern_id)
                if intern is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Intern profile not found"
                    )
                
                # Check if intern is in any batch where TL is assigned
                if intern.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot delete evaluation for intern not in any batch"
                    )
                
                # Check if TL is assigned to intern's batch (any TL position)
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, intern.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete evaluations for interns in their assigned batches"
                    )
            elif current_user.role == "ADMIN":
                # Admin can delete any evaluation
                pass
            else:
                # Other roles not allowed
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to delete evaluations"
                )
        
        # Call parent delete
        super().delete(db, evaluation_id)

    def _get_profile(self, db: Session, profile_id: UUID, label: str) -> Profile:
        profile = db.get(Profile, profile_id)
        if profile is None:
            raise ConflictError(f"{label.capitalize()} profile '{profile_id}' does not exist.")
        return profile


evaluation_service = EvaluationService()
