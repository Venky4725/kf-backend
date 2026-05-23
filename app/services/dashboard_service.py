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

class DashboardService:
    def get_admin_dashboard_stats(self, db: Session, current_user) -> dict:
        """
        Consolidated dashboard statistics for Admin/TL.
        Optimized to fetch multiple metrics in fewer queries.
        """
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        
        # 1. Attendance Distribution (Last 30 days)
        attendance_dist = attendance_service.get_attendance_distribution(
            db, 
            start_date=thirty_days_ago, 
            end_date=today, 
            current_user=current_user
        )
        
        # 2. Evaluation Stats
        evaluation_stats = evaluation_service.get_evaluation_stats(
            db, 
            current_user=current_user
        )
        
        # 3. General Counts
        # Fetch counts in parallel if possible, or targeted queries
        counts_query = db.query(
            func.count(Profile.id).filter(Profile.role == "INTERN", Profile.is_active == True).label("active_interns"),
            func.count(Batch.id).label("total_batches")
        )
        
        # RBAC for counts
        if current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if tl_batch_ids:
                counts_query = counts_query.filter(
                    or_(
                        Batch.first_tech_lead_id == current_user.id,
                        Batch.second_tech_lead_id == current_user.id,
                        Batch.third_tech_lead_id == current_user.id
                    )
                )
            else:
                # No batches assigned
                return {
                    "attendance": attendance_dist,
                    "evaluations": evaluation_stats,
                    "active_interns": 0,
                    "total_batches": 0,
                    "recent_trends": []
                }
        
        counts = counts_query.one()
        
        # 4. Recent Trends (Combined Attendance & Evaluations if needed)
        # For now, just return what's already calculated in distribution and eval_stats
        
        return {
            "attendance": attendance_dist,
            "evaluations": evaluation_stats,
            "active_interns": counts.active_interns,
            "total_batches": counts.total_batches,
            "server_time": today.isoformat()
        }

dashboard_service = DashboardService()
