from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError


class NotificationService(CRUDService[Notification]):
    model = Notification
    resource_name = "Notification"
    table_name = "notifications"

    def create_notification(self, db: Session, payload: NotificationCreate) -> Notification:
        self._ensure_profile_exists(db, payload.user_id)
        return self.create(
            db,
            {
                "user_id": payload.user_id,
                "title": payload.title.strip(),
                "message": payload.message.strip(),
                "is_read": False,
            },
        )

    def list_notifications(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: UUID | None = None,
        is_read: bool | None = None,
    ) -> list[Notification]:
        query = db.query(Notification)
        if user_id:
            query = query.filter(Notification.user_id == user_id)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

    def update_notification(
        self,
        db: Session,
        notification_id: UUID,
        payload: NotificationUpdate,
    ) -> Notification:
        return self.update(db, notification_id, {"is_read": payload.is_read})

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        from app.models.profile import Profile

        profile = db.get(Profile, profile_id)
        if profile is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")
        if not profile.is_active:
            raise ConflictError(f"Cannot send notification to inactive user.")


notification_service = NotificationService()
