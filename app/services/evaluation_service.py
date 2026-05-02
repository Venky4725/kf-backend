from uuid import UUID

from sqlalchemy.orm import Session

from app.models.evaluation import Evaluation
from app.models.profile import Profile
from app.schemas.evaluation import EvaluationCreate, EvaluationUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError, ValidationError


class EvaluationService(CRUDService[Evaluation]):
    model = Evaluation
    resource_name = "Evaluation"
    table_name = "evaluations"

    def create_evaluation(self, db: Session, payload: EvaluationCreate) -> Evaluation:
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
    ) -> list[Evaluation]:
        query = db.query(Evaluation)
        if intern_id:
            query = query.filter(Evaluation.intern_id == intern_id)
        if reviewed_by:
            query = query.filter(Evaluation.reviewed_by == reviewed_by)
        return query.order_by(Evaluation.week_number.desc(), Evaluation.created_at.desc()).offset(skip).limit(limit).all()

    def update_evaluation(self, db: Session, evaluation_id: UUID, payload: EvaluationUpdate) -> Evaluation:
        updates = payload.model_dump(exclude_unset=True)
        if "score" in updates and updates["score"] is not None and (updates["score"] < 0 or updates["score"] > 5):
            raise ValidationError("Score must be between 0 and 5.")
        if "feedback" in updates and updates["feedback"] is not None:
            updates["feedback"] = updates["feedback"].strip()
        return self.update(db, evaluation_id, updates)

    def _get_profile(self, db: Session, profile_id: UUID, label: str) -> Profile:
        profile = db.get(Profile, profile_id)
        if profile is None:
            raise ConflictError(f"{label.capitalize()} profile '{profile_id}' does not exist.")
        return profile


evaluation_service = EvaluationService()
