# app/routers/dashboard.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Consolidated dashboard statistics for Admin/TL.
    Reduces multiple round-trips to a single call.
    """
    return dashboard_service.get_admin_dashboard_stats(db, current_user)


@router.get("/stats/attendance")
def get_dashboard_attendance_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch only attendance distribution for dashboard."""
    return dashboard_service.get_attendance_stats(db, current_user)


@router.get("/stats/evaluations")
def get_dashboard_evaluation_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch only evaluation stats for dashboard."""
    return dashboard_service.get_evaluation_stats(db, current_user)


@router.get("/stats/counts")
def get_dashboard_counts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Fetch only general counts (active interns, total batches) for dashboard."""
    return dashboard_service.get_general_counts(db, current_user)
