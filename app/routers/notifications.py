# app/routers/notifications.py

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.notification import NotificationCreate, NotificationResponse, NotificationUpdate
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
def get_notifications(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID | None = None,
    is_read: bool | None = None,
    db: Session = Depends(get_db),
):
    return notification_service.list_notifications(db, skip=skip, limit=limit, user_id=user_id, is_read=is_read)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
):
    return notification_service.get(db, notification_id)


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
):
    return notification_service.create_notification(db, payload)


@router.put("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: UUID,
    payload: NotificationUpdate,
    db: Session = Depends(get_db),
):
    return notification_service.update_notification(db, notification_id, payload)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    notification_service.delete(db, notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
