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
