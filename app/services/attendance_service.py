from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError, ValidationError

VALID_ATTENDANCE_STATUSES = {"PRESENT", "ABSENT", "LEAVE"}


class AttendanceService(CRUDService[Attendance]):
    model = Attendance
    resource_name = "Attendance"
    table_name = "attendance"

    def create_attendance(self, db: Session, payload: AttendanceCreate) -> Attendance:
        self._ensure_profile_exists(db, payload.user_id)
        status = self._normalize_status(payload.status)

        duplicate = (
            db.query(Attendance)
            .filter(Attendance.user_id == payload.user_id, Attendance.day == payload.day)
            .first()
        )
        if duplicate is not None:
            raise ConflictError("Attendance is already marked for this user on the given day.")

        return self.create(
            db,
            {
                "user_id": payload.user_id,
                "day": payload.day,
                "status": status,
            },
        )

    def list_attendance(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: UUID | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> list[Attendance]:
        query = db.query(Attendance)
        if user_id:
            query = query.filter(Attendance.user_id == user_id)
        if start:
            query = query.filter(Attendance.day >= start)
        if end:
            query = query.filter(Attendance.day <= end)
        return query.order_by(Attendance.day.desc(), Attendance.created_at.desc()).offset(skip).limit(limit).all()

    def update_attendance(self, db: Session, attendance_id: UUID, payload: AttendanceUpdate) -> Attendance:
        return self.update(db, attendance_id, {"status": self._normalize_status(payload.status)})

    def _normalize_status(self, status: str) -> str:
        normalized = status.strip().upper()
        if normalized not in VALID_ATTENDANCE_STATUSES:
            raise ValidationError(
                f"Attendance status must be one of: {', '.join(sorted(VALID_ATTENDANCE_STATUSES))}."
            )
        return normalized

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        from app.models.profile import Profile

        if db.get(Profile, profile_id) is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")


attendance_service = AttendanceService()
