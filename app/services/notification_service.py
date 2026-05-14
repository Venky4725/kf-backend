from uuid import UUID
import logging

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from app.models.notification import Notification
from app.models.profile import Profile
from app.schemas.notification import NotificationBroadcast, NotificationCreate, NotificationUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError

logger = logging.getLogger(__name__)


class NotificationService(CRUDService[Notification]):
    model = Notification
    resource_name = "Notification"
    table_name = "notifications"

    def create_notification(self, db: Session, payload: NotificationCreate) -> Notification:
        try:
            self._ensure_profile_exists(db, payload.user_id)
            
            # Validate sender if provided
            if payload.sender_id:
                sender = db.get(Profile, payload.sender_id)
                if not sender:
                    raise ConflictError(f"Sender profile '{payload.sender_id}' does not exist.")
            
            notification_data = {
                "user_id": payload.user_id,
                "title": payload.title.strip(),
                "message": payload.message.strip(),
                "is_read": False,
            }
            
            # Add sender_id if provided
            if payload.sender_id:
                notification_data["sender_id"] = payload.sender_id
            
            # Only add type and is_broadcast if they exist in the model
            try:
                notification_data["type"] = payload.type
                notification_data["is_broadcast"] = False
            except AttributeError:
                # Columns don't exist yet, skip them
                pass
            
            return self.create(db, notification_data)
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise

    def broadcast_notification(self, db: Session, payload: NotificationBroadcast, current_user) -> dict:
        """Create broadcast notification for all active users - ADMIN ONLY"""
        # Only ADMIN can broadcast
        if current_user.role != "ADMIN":
            from fastapi import HTTPException, status as http_status
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only administrators can broadcast notifications"
            )
        
        try:
            # Get all active users
            active_users = db.query(Profile).filter(Profile.is_active == True).all()
            
            created_count = 0
            for user in active_users:
                try:
                    notification = Notification(
                        user_id=user.id,
                        sender_id=current_user.id,  # CRITICAL: Set sender_id
                        title="System Notification",
                        message=payload.message.strip(),
                        is_read=False,
                    )
                    
                    # Try to set type and is_broadcast if columns exist
                    try:
                        notification.type = payload.type
                        notification.is_broadcast = True
                    except AttributeError:
                        pass
                    
                    db.add(notification)
                    created_count += 1
                except Exception as e:
                    logger.warning(f"Failed to create notification for user {user.id}: {e}")
                    continue
            
            db.commit()
            
            return {
                "message": "Broadcast notification sent successfully",
                "recipients": created_count
            }
        except Exception as e:
            logger.error(f"Error broadcasting notification: {e}")
            db.rollback()
            raise

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
    ) -> list[dict]:
        try:
            from sqlalchemy import or_
            
            # Use joinedload to eagerly load sender relationship
            query = db.query(Notification).options(joinedload(Notification.sender))
            
            # CRITICAL FIX: Show BOTH received AND sent notifications
            if current_user:
                query = query.filter(
                    or_(
                        Notification.user_id == current_user.id,      # received
                        Notification.sender_id == current_user.id     # sent
                    )
                )
            elif user_id:
                # Fallback if no current_user but user_id provided
                query = query.filter(
                    or_(
                        Notification.user_id == user_id,
                        Notification.sender_id == user_id
                    )
                )
            
            # Apply is_read filter only if explicitly provided
            if is_read is not None:
                query = query.filter(Notification.is_read == is_read)
            
            # Apply search filter only if provided (search in title and message)
            if search and search.strip():
                search_pattern = f"%{search.strip()}%"
                query = query.filter(
                    (Notification.title.ilike(search_pattern)) |
                    (Notification.message.ilike(search_pattern))
                )
            
            # Apply type filter only if provided and column exists
            if type and type.strip():
                try:
                    query = query.filter(Notification.type.ilike(type.strip()))
                except AttributeError:
                    # type column doesn't exist yet, skip this filter
                    logger.warning("Notification.type column not found, skipping type filter")
                    pass
            
            # Execute query with error handling
            try:
                results = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
                
                # Build response with sender_name and is_sender flag
                response = []
                for notification in results:
                    # Determine if current user is the sender
                    is_sender = False
                    if current_user and hasattr(notification, 'sender_id'):
                        is_sender = notification.sender_id == current_user.id
                    
                    notification_dict = {
                        "id": notification.id,
                        "user_id": notification.user_id,
                        "sender_id": notification.sender_id if hasattr(notification, 'sender_id') else None,
                        "sender_name": notification.sender.name if hasattr(notification, 'sender') and notification.sender else None,
                        "is_sender": is_sender,
                        "title": notification.title,
                        "message": notification.message,
                        "type": notification.type if hasattr(notification, 'type') else None,
                        "is_read": notification.is_read,
                        "is_broadcast": notification.is_broadcast if hasattr(notification, 'is_broadcast') else False,
                        "created_at": notification.created_at,
                        "edited_at": notification.edited_at if hasattr(notification, 'edited_at') else None,
                    }
                    response.append(notification_dict)
                
                return response if response else []
            except SQLAlchemyError as e:
                logger.error(f"Database error in list_notifications: {e}")
                # Return empty list instead of crashing
                return []
                
        except Exception as e:
            logger.error(f"Unexpected error in list_notifications: {e}")
            # Return empty list instead of crashing
            return []

    def update_notification(
        self,
        db: Session,
        notification_id: UUID,
        payload: NotificationUpdate,
        current_user=None,
    ) -> Notification:
        try:
            from fastapi import HTTPException, status as http_status
            
            if not current_user:
                raise HTTPException(
                    status_code=http_status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            notification = self.get(db, notification_id)
            
            # Build update data from provided fields only
            update_data = {}
            
            # Check if user is trying to edit content (title/message)
            is_editing_content = payload.title is not None or payload.message is not None
            
            if is_editing_content:
                # Only ADMIN and TECH_LEAD can edit content
                if current_user.role not in ["ADMIN", "TECHNICAL_LEAD"]:
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="Only ADMIN and TECH_LEAD can edit notifications"
                    )
                
                if payload.title is not None:
                    update_data["title"] = payload.title.strip()
                if payload.message is not None:
                    update_data["message"] = payload.message.strip()
            
            # Anyone can mark their own notifications as read
            if payload.is_read is not None:
                if notification.user_id != current_user.id:
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="You can only mark your own notifications as read"
                    )
                update_data["is_read"] = payload.is_read
            
            # If no fields to update, return notification as-is
            if not update_data:
                return notification
            
            return self.update(db, notification_id, update_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating notification: {e}")
            raise

    def delete(self, db: Session, notification_id: UUID, current_user=None) -> None:
        """Delete notification - ADMIN can delete any, TECH_LEAD can delete intern notifications only"""
        try:
            from fastapi import HTTPException, status as http_status
            
            if not current_user:
                raise HTTPException(
                    status_code=http_status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            notification = self.get(db, notification_id)
            
            # Get the receiver's profile to check their role
            receiver = db.get(Profile, notification.user_id)
            if not receiver:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Notification receiver not found"
                )
            
            # ADMIN can delete any notification
            if current_user.role == "ADMIN":
                super().delete(db, notification_id)
                logger.info(f"Notification {notification_id} deleted by ADMIN {current_user.id}")
                return
            
            # TECH_LEAD can only delete notifications sent to INTERNS
            if current_user.role == "TECHNICAL_LEAD":
                if receiver.role != "INTERN":
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="Tech leads can only delete notifications sent to interns"
                    )
                super().delete(db, notification_id)
                logger.info(f"Notification {notification_id} deleted by TECH_LEAD {current_user.id}")
                return
            
            # INTERN cannot delete any notification
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Interns cannot delete notifications"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            raise

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        profile = db.get(Profile, profile_id)
        if profile is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")
        if not profile.is_active:
            raise ConflictError(f"Cannot send notification to inactive user.")


notification_service = NotificationService()
