from app.services.auth_service import auth_service
from app.services.attendance_service import attendance_service
from app.services.batch_service import batch_service
from app.services.evaluation_service import evaluation_service
from app.services.notification_service import notification_service
from app.services.profile_service import profile_service
from app.services.submission_service import submission_service
from app.services.task_service import task_service

__all__ = [
    "auth_service",
    "attendance_service",
    "batch_service",
    "evaluation_service",
    "notification_service",
    "profile_service",
    "submission_service",
    "task_service",
]
