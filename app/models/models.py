"""Compatibility exports for code that still imports ``app.models.models``."""

from app.models.attendance import Attendance
from app.models.audit_log import AuditLog
from app.models.batch import Batch
from app.models.evaluation import Evaluation
from app.models.notification import Notification
from app.models.profile import Profile
from app.models.submission import Submission
from app.models.task import Task

__all__ = [
    "Attendance",
    "AuditLog",
    "Batch",
    "Evaluation",
    "Notification",
    "Profile",
    "Submission",
    "Task",
]
