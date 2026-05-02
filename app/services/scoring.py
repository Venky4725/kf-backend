from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.batch import Batch
from app.models.evaluation import Evaluation
from app.models.submission import Submission

PRESENT_STATUS = "PRESENT"


def current_week_for_batch(start_date: date, *, today: date | None = None) -> int:
    today = today or date.today()
    if today < start_date:
        return 0
    return ((today - start_date).days // 7) + 1


def attendance_rate(
    db: Session,
    *,
    intern_id: UUID,
    week_number: int,
    batch_start: date,
    work_days_per_week: int = 6,
) -> float:
    week_start = batch_start + timedelta(days=(week_number - 1) * 7)
    week_end = week_start + timedelta(days=work_days_per_week - 1)
    present_days = (
        db.query(func.count(Attendance.id))
        .filter(
            Attendance.user_id == intern_id,
            Attendance.day >= week_start,
            Attendance.day <= week_end,
            Attendance.status == PRESENT_STATUS,
        )
        .scalar()
        or 0
    )
    return min(present_days / work_days_per_week, 1.0)


def submission_rate(
    db: Session,
    *,
    intern_id: UUID,
    week_number: int,
    batch_start: date,
    work_days_per_week: int = 6,
) -> float:
    week_start = batch_start + timedelta(days=(week_number - 1) * 7)
    week_end = week_start + timedelta(days=work_days_per_week - 1)
    submitted_days = (
        db.query(func.count(func.distinct(Submission.submitted_for)))
        .filter(
            Submission.user_id == intern_id,
            Submission.submitted_for >= week_start,
            Submission.submitted_for <= week_end,
        )
        .scalar()
        or 0
    )
    return min(submitted_days / work_days_per_week, 1.0)


def average_evaluation_score(db: Session, *, intern_id: UUID) -> float:
    average = db.query(func.avg(Evaluation.score)).filter(Evaluation.intern_id == intern_id).scalar()
    return round(float(average or 0), 2)


def batch_completion_ratio(*, batch: Batch, today: date | None = None, work_days_per_week: int = 6) -> float:
    today = today or date.today()
    if today < batch.start_date:
        return 0.0
    elapsed_days = (today - batch.start_date).days + 1
    elapsed_weeks = max(1, (elapsed_days + 6) // 7)
    total_elapsed_work_days = elapsed_weeks * work_days_per_week
    return min(total_elapsed_work_days / work_days_per_week, 1.0)
