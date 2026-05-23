# app/services/dashboard_service.py

from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import logging

from app.models.attendance import Attendance
from app.models.evaluation import Evaluation
from app.models.profile import Profile
from app.models.batch import Batch
from app.services.attendance_service import attendance_service
from app.services.evaluation_service import evaluation_service

logger = logging.getLogger(__name__)

import time

class DashboardService:
    def get_admin_dashboard_stats(self, db: Session, current_user) -> dict:
        """
        Consolidated dashboard statistics for Admin/TL.
        Optimized to fetch multiple metrics in fewer queries.
        """
        start_time = time.time()
        today = date.today()
        
        # Pre-fetch TL batch IDs
        tl_batch_ids = None
        if current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if not tl_batch_ids:
                return {
                    "attendance": {"present_count": 0, "absent_count": 0, "late_count": 0, "leave_count": 0, "total_count": 0},
                    "evaluations": {"total_evaluations": 0, "average_score": 0, "min_score": 0, "max_score": 0, "evaluations_by_week": []},
                    "active_interns": 0,
                    "total_batches": 0,
                    "server_time": today.isoformat()
                }

        # Use granular methods to build consolidated response
        attendance_dist = self.get_attendance_stats(db, current_user, tl_batch_ids)
        evaluation_stats = self.get_evaluation_stats(db, current_user, tl_batch_ids)
        counts = self.get_general_counts(db, current_user, tl_batch_ids)
        
        end_time = time.time()
        logger.info(f"Dashboard: Consolidated stats took {end_time-start_time:.4f}s")
        
        return {
            "attendance": attendance_dist,
            "evaluations": evaluation_stats,
            "active_interns": counts["active_interns"],
            "total_batches": counts["total_batches"],
            "server_time": today.isoformat(),
            "load_time_ms": int((end_time - start_time) * 1000)
        }

    def get_attendance_stats(self, db: Session, current_user, tl_batch_ids=None) -> dict:
        """Fetch only attendance distribution."""
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        
        if tl_batch_ids is None and current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if not tl_batch_ids:
                return {"present_count": 0, "absent_count": 0, "late_count": 0, "leave_count": 0, "total_count": 0}

        return attendance_service.get_attendance_distribution(
            db, 
            start_date=thirty_days_ago, 
            end_date=today, 
            current_user=current_user,
            tl_batch_ids=tl_batch_ids
        )

    def get_evaluation_stats(self, db: Session, current_user, tl_batch_ids=None) -> dict:
        """Fetch only evaluation statistics."""
        if tl_batch_ids is None and current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if not tl_batch_ids:
                return {"total_evaluations": 0, "average_score": 0, "min_score": 0, "max_score": 0, "evaluations_by_week": []}

        return evaluation_service.get_evaluation_stats(
            db, 
            current_user=current_user,
            tl_batch_ids=tl_batch_ids
        )

    def get_general_counts(self, db: Session, current_user, tl_batch_ids=None) -> dict:
        """Fetch general counts (active interns, total batches)."""
        if tl_batch_ids is None and current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if not tl_batch_ids:
                return {"active_interns": 0, "total_batches": 0}

        counts_query = db.query(
            func.count(Profile.id).filter(Profile.role == "INTERN", Profile.is_active == True).label("active_interns"),
            func.count(Batch.id).label("total_batches")
        )
        
        if current_user.role == "TECHNICAL_LEAD":
            counts_query = db.query(
                func.count(Profile.id).filter(
                    Profile.role == "INTERN", 
                    Profile.is_active == True,
                    Profile.batch_id.in_(tl_batch_ids)
                ).label("active_interns"),
                func.count(Batch.id).filter(
                    or_(
                        Batch.first_tech_lead_id == current_user.id,
                        Batch.second_tech_lead_id == current_user.id,
                        Batch.third_tech_lead_id == current_user.id
                    )
                ).label("total_batches")
            )
        
        counts = counts_query.one()
        return {
            "active_interns": counts.active_interns,
            "total_batches": counts.total_batches
        }

dashboard_service = DashboardService()
