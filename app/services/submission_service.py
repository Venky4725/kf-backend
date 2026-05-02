from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.submission import Submission
from app.models.profile import Profile
from app.schemas.submission import SubmissionCreate, SubmissionUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError


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
    ) -> list[Submission]:
        query = db.query(Submission)
        if user_id:
            query = query.filter(Submission.user_id == user_id)
        if submitted_for:
            query = query.filter(Submission.submitted_for == submitted_for)
        submissions = query.order_by(Submission.submitted_for.desc(), Submission.created_at.desc()).offset(skip).limit(limit).all()
        
        # Add submitted_by_name by joining with profile
        result = []
        for sub in submissions:
            profile = db.query(Profile).filter(Profile.id == sub.user_id).first()
            if profile:
                sub.submitted_by_name = profile.name
            else:
                sub.submitted_by_name = None
            result.append(sub)
        
        return result

    def update_submission(self, db: Session, submission_id: UUID, payload: SubmissionUpdate) -> Submission:
        return self.update(db, submission_id, {"content": payload.content.strip()})

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        from app.models.profile import Profile

        if db.get(Profile, profile_id) is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")


submission_service = SubmissionService()
