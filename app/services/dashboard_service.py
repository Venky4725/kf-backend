from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc
import logging
import time

from app.models.attendance import Attendance
from app.models.evaluation import Evaluation
from app.models.profile import Profile
from app.models.batch import Batch
from app.models.task import Task
from app.models.submission import Submission
from app.models.notification import Notification
from app.services.attendance_service import attendance_service
from app.services.evaluation_service import evaluation_service

logger = logging.getLogger(__name__)

class DashboardService:
    def get_admin_dashboard_stats(self, db: Session, current_user) -> dict:
        """
        Consolidated dashboard statistics for Admin/TL/Intern.
        Optimized to fetch multiple metrics in fewer queries.
        """
        start_time = time.time()
        today = date.today()
        
        # Ensure we have fresh user data (avoid stale role/batch info)
        db.refresh(current_user)
        
        # Pre-fetch TL batch IDs
        tl_batch_ids = None
        if current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            logger.info(f"Dashboard TL ID: {current_user.id}, Fetched Batch IDs: {tl_batch_ids}")
            if not tl_batch_ids:
                logger.warning(f"Technical Lead {current_user.id} has no assigned batches. Returning empty stats.")
                return self._get_empty_stats(today)
        
        # Use granular methods to build consolidated response
        attendance_dist = self.get_attendance_stats(db, current_user, tl_batch_ids)
        evaluation_stats = self.get_evaluation_stats(db, current_user, tl_batch_ids)
        counts = self.get_general_counts(db, current_user, tl_batch_ids)
        recent_submissions = self.get_recent_submissions(db, current_user, tl_batch_ids)
        intern_distribution = self.get_intern_distribution(db, current_user, tl_batch_ids)
        
        end_time = time.time()
        logger.info(f"Dashboard ({current_user.role}): Consolidated stats took {end_time-start_time:.4f}s")
        
        response = {
            "attendance": attendance_dist,
            "evaluations": evaluation_stats,
            "counts": counts,
            "recent_submissions": recent_submissions,
            "intern_distribution": intern_distribution,
            # Flattened counts for direct access (backward compatibility)
            "active_interns": counts.get("interns", 0),
            "interns_count": counts.get("interns", 0),
            "total_batches": counts.get("batches", 0),
            "batches_count": counts.get("batches", 0),
            "total_tech_leads": counts.get("tech_leads", 0),
            "tech_leads_count": counts.get("tech_leads", 0),
            "total_tasks": counts.get("tasks", 0),
            "tasks_count": counts.get("tasks", 0),
            "total_submissions": counts.get("submissions", 0),
            "submissions_count": counts.get("submissions", 0),
            "total_evaluations": counts.get("evaluations", 0),
            "evaluations_count": counts.get("evaluations", 0),
            "total_notifications": counts.get("notifications", 0),
            "notifications_count": counts.get("notifications", 0),
            "server_time": today.isoformat(),
            "load_time_ms": int((end_time - start_time) * 1000)
        }
        
        return response

    def get_attendance_stats(self, db: Session, current_user, tl_batch_ids=None) -> dict:
        """Fetch only attendance distribution."""
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        
        return attendance_service.get_attendance_distribution(
            db, 
            start_date=thirty_days_ago, 
            end_date=today, 
            current_user=current_user,
            tl_batch_ids=tl_batch_ids
        )

    def get_evaluation_stats(self, db: Session, current_user, tl_batch_ids=None) -> dict:
        """Fetch only evaluation statistics."""
        return evaluation_service.get_evaluation_stats(
            db, 
            current_user=current_user,
            tl_batch_ids=tl_batch_ids
        )

    def get_general_counts(self, db: Session, current_user, tl_batch_ids=None) -> dict:
        """Fetch general counts with strict role-based filtering."""
        if current_user.role == "ADMIN":
            return {
                # System-wide core counts
                "interns": db.query(func.count(Profile.id)).filter(Profile.role == "INTERN", Profile.is_active == True).scalar(),
                "batches": db.query(func.count(Batch.id)).scalar(),
                "tech_leads": db.query(func.count(Profile.id)).filter(Profile.role == "TECHNICAL_LEAD", Profile.is_active == True).scalar(),
                
                # Activity counts (Role-specific)
                "tasks": db.query(func.count(Task.id)).filter(Task.created_by == current_user.id).scalar(),
                "submissions": 0, # Admins don't have submissions
                "evaluations": db.query(func.count(Evaluation.id)).filter(Evaluation.reviewed_by == current_user.id).scalar(),
                "notifications": db.query(func.count(Notification.id)).filter(
                    or_(
                        Notification.sender_id == current_user.id,
                        Notification.is_broadcast == True
                    )
                ).scalar()
            }
        
        elif current_user.role == "TECHNICAL_LEAD":
            if tl_batch_ids is None:
                from app.core.tech_lead_utils import get_tech_lead_batch_ids
                tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)

            # Strict batch filtering for TL statistics
            # Statistics MUST be calculated from TL's assigned batches
            intern_count = db.query(func.count(Profile.id)).filter(
                Profile.role == "INTERN", 
                Profile.is_active == True,
                Profile.batch_id.in_(tl_batch_ids) if tl_batch_ids else False
            ).scalar() if tl_batch_ids else 0

            submission_count = db.query(func.count(Submission.id)).join(Profile, Submission.user_id == Profile.id).filter(
                Profile.batch_id.in_(tl_batch_ids) if tl_batch_ids else False
            ).scalar() if tl_batch_ids else 0

            evaluation_count = db.query(func.count(Evaluation.id)).join(Profile, Evaluation.intern_id == Profile.id).filter(
                Profile.batch_id.in_(tl_batch_ids) if tl_batch_ids else False
            ).scalar() if tl_batch_ids else 0

            # Debug logging for Technical Lead stats as requested
            logger.info(f"DEBUG Dashboard TL: id={current_user.id}, assigned_batch_ids={tl_batch_ids}")
            logger.info(f"DEBUG Dashboard TL counts: interns={intern_count}, submissions={submission_count}, evaluations={evaluation_count}")

            return {
                "interns": intern_count,
                "batches": len(tl_batch_ids) if tl_batch_ids else 0,
                "tech_leads": 0, # TLs don't manage other TLs
                
                # Activity counts (Role-specific)
                "tasks": db.query(func.count(Task.id)).filter(
                    or_(Task.created_by == current_user.id, Task.assigned_to == current_user.id)
                ).scalar(),
                "submissions": submission_count,
                "evaluations": evaluation_count,
                "notifications": db.query(func.count(Notification.id)).filter(
                    or_(
                        Notification.user_id == current_user.id,
                        Notification.sender_id == current_user.id
                    )
                ).scalar()
            }
        
        elif current_user.role == "INTERN":
            from app.utils.role_utils import normalize_role
            normalized_intern_role = normalize_role(current_user.intern_role)
            
            intern_task_count = db.query(func.count(Task.id)).filter(
                Task.batch_id == current_user.batch_id,
                or_(
                    Task.assigned_to == current_user.id,
                    Task.role == normalized_intern_role,
                    (Task.assigned_to == None) & (Task.role == "ALL")
                )
            ).scalar()
            
            return {
                "interns": 0, "batches": 0, "tech_leads": 0,
                "tasks": intern_task_count,
                "submissions": db.query(func.count(Submission.id)).filter(Submission.user_id == current_user.id).scalar(),
                "evaluations": db.query(func.count(Evaluation.id)).filter(Evaluation.intern_id == current_user.id).scalar(),
                "notifications": db.query(func.count(Notification.id)).filter(
                    or_(
                        Notification.user_id == current_user.id,
                        Notification.is_broadcast == True
                    )
                ).scalar()
            }
        
        return self._get_empty_stats(date.today())["counts"]

    def get_recent_submissions(self, db: Session, current_user, tl_batch_ids=None, limit=3) -> list:
        """Fetch latest submissions with strict role-based filtering."""
        query = db.query(Submission).options(joinedload(Submission.profile))
        
        if current_user.role == "TECHNICAL_LEAD":
            if tl_batch_ids is None:
                from app.core.tech_lead_utils import get_tech_lead_batch_ids
                tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            
            if tl_batch_ids:
                query = query.join(Profile, Submission.user_id == Profile.id).filter(
                    Profile.batch_id.in_(tl_batch_ids)
                )
            else:
                return []
        elif current_user.role == "INTERN":
            query = query.filter(Submission.user_id == current_user.id)
        elif current_user.role == "ADMIN":
            # Admins can see all recent submissions for system monitoring
            pass
        
        submissions = query.order_by(desc(Submission.created_at)).limit(limit).all()
        
        return [
            {
                "id": str(sub.id),
                "submitter_id": str(sub.user_id),
                "intern_name": sub.profile.name if sub.profile else "Unknown",
                "submitter_name": sub.profile.name if sub.profile else "Unknown",
                "batch_name": sub.profile.batch.name if sub.profile and sub.profile.batch else "Unknown",
                "submitted_for": sub.submitted_for.isoformat(),
                "created_at": sub.created_at.isoformat(),
                "content": sub.content[:100] + "..." if len(sub.content) > 100 else sub.content
            }
            for sub in submissions
        ]

    def get_intern_distribution(self, db: Session, current_user, tl_batch_ids=None) -> list:
        """Get intern counts grouped by batch with strict role-based filtering."""
        if current_user.role == "INTERN":
            return []

        query = db.query(
            Batch.name.label("batch_name"),
            func.count(Profile.id).label("intern_count")
        ).join(Profile, Batch.id == Profile.batch_id).filter(Profile.role == "INTERN")
        
        if current_user.role == "TECHNICAL_LEAD":
            if tl_batch_ids is None:
                from app.core.tech_lead_utils import get_tech_lead_batch_ids
                tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            
            if tl_batch_ids:
                query = query.filter(Batch.id.in_(tl_batch_ids))
            else:
                return []
        
        distribution = query.group_by(Batch.name).all()
        
        return [{"batch_name": d.batch_name, "intern_count": d.intern_count} for d in distribution]

    def _get_empty_stats(self, today: date) -> dict:
        return {
            "attendance": {"present_count": 0, "absent_count": 0, "late_count": 0, "leave_count": 0, "total_count": 0},
            "evaluations": {"total_evaluations": 0, "average_score": 0, "min_score": 0, "max_score": 0, "evaluations_by_week": []},
            "counts": {"interns": 0, "batches": 0, "tech_leads": 0, "tasks": 0, "submissions": 0, "evaluations": 0, "notifications": 0},
            "recent_submissions": [],
            "intern_distribution": [],
            "active_interns": 0,
            "total_batches": 0,
            "server_time": today.isoformat()
        }

dashboard_service = DashboardService()
