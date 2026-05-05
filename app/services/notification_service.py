from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.profile import Profile
from app.schemas.notification import NotificationBroadcast, NotificationCreate, NotificationUpdate
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
                "type": payload.type,
                "is_read": False,
                "is_broadcast": False,
            },
        )

    def broadcast_notification(self, db: Session, payload: NotificationBroadcast, current_user) -> dict:
        """Create broadcast notification for all active users"""
        # Get all active users
        active_users = db.query(Profile).filter(Profile.is_active == True).all()
        
        created_count = 0
        for user in active_users:
            notification = Notification(
                user_id=user.id,
                title="System Notification",
                message=payload.message.strip(),
                type=payload.type,
                is_read=False,
                is_broadcast=True,
            )
            db.add(notification)
            created_count += 1
        
        db.commit()
        
        return {
            "message": "Broadcast notification sent successfully",
            "recipients": created_count
        }

    def list_notifications(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        user_id: UUID | None = None,
        is_read: bool | None = None,
        search: str | None = None,
        type: str | None = None,
        current_user=None,
    ) -> list[Notification]:
        query = db.query(Notification)
        
        # Filter by current user - only show their notifications
        if current_user:
            query = query.filter(Notification.user_id == current_user.id)
        elif user_id:
            # Fallback if no current_user but user_id provided
            query = query.filter(Notification.user_id == user_id)
        
        # Apply is_read filter
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        
        # Apply search filter (search in title and message)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Notification.title.ilike(search_pattern)) |
                (Notification.message.ilike(search_pattern))
            )
        
        # Apply type filter
        if type:
            query = query.filter(Notification.type.ilike(type))
        
        return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

    def update_notification(
        self,
        db: Session,
        notification_id: UUID,
        payload: NotificationUpdate,
    ) -> Notification:
        return self.update(db, notification_id, {"is_read": payload.is_read})

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        profile = db.get(Profile, profile_id)
        if profile is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")
        if not profile.is_active:
            raise ConflictError(f"Cannot send notification to inactive user.")


notification_service = NotificationService()
