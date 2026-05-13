# app/routers/attendance.py

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.attendance import (
    AttendanceCreate, 
    AttendanceResponse, 
    AttendanceUpdate,
    AttendanceDistribution,
    InternAttendanceAnalytics,
    PendingAttendanceIntern
)
from app.services.attendance_service import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard/summary")
def get_dashboard_summary(
    batch_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get dashboard summary with overall statistics.
    
    Returns:
    - Total attendance records
    - Distribution by status (present, absent, late, leave)
    - Attendance rate
    - Recent trends
    
    RBAC:
    - ADMIN: All attendance
    - TECHNICAL_LEAD: Only their batches
    """
    distribution = attendance_service.get_attendance_distribution(
        db,
        batch_id=batch_id,
        start_date=start_date,
        end_date=end_date,
        current_user=current_user
    )
    
    # Calculate attendance rate (present + late / total)
    total = distribution['total_count']
    if total > 0:
        attended = distribution['present_count'] + distribution['late_count']
        attendance_rate = round((attended / total) * 100, 2)
    else:
        attendance_rate = 0.0
    
    return {
        "total_records": total,
        "present": distribution['present_count'],
        "absent": distribution['absent_count'],
        "late": distribution['late_count'],
        "leave": distribution['leave_count'],
        "attendance_rate": attendance_rate,
        "distribution": distribution
    }


@router.get("/dashboard/distribution", response_model=AttendanceDistribution)
def get_dashboard_distribution(
    batch_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get attendance distribution for dashboard pie charts.
    
    Query params:
    - batch_id: Filter by specific batch
    - start_date: Start date for date range
    - end_date: End date for date range
    
    RBAC:
    - ADMIN: All attendance
    - TECHNICAL_LEAD: Only their batches
    """
    return attendance_service.get_attendance_distribution(
        db,
        batch_id=batch_id,
        start_date=start_date,
        end_date=end_date,
        current_user=current_user
    )


@router.get("/dashboard/trends")
def get_dashboard_trends(
    batch_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get attendance trends over time for dashboard charts.
    
    Query params:
    - batch_id: Filter by specific batch
    - start_date: Start date for date range
    - end_date: End date for date range
    - days: Number of days to include (default 30)
    
    Returns daily attendance counts by status.
    
    RBAC:
    - ADMIN: All attendance
    - TECHNICAL_LEAD: Only their batches
    """
    from datetime import timedelta
    from sqlalchemy import func
    from app.models.attendance import Attendance
    from app.models.profile import Profile
    from app.models.batch import Batch
    from sqlalchemy import or_
    
    # Calculate date range
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=days)
    
    # Base query
    query = db.query(
        Attendance.day,
        Attendance.status,
        func.count(Attendance.id).label('count')
    ).join(Profile, Attendance.user_id == Profile.id)
    
    # RBAC: Tech Lead can only see their batches
    if current_user and current_user.role == "TECHNICAL_LEAD":
        query = query.join(Batch, Profile.batch_id == Batch.id).filter(
            or_(
                Batch.first_tech_lead_id == current_user.id,
                Batch.second_tech_lead_id == current_user.id
            )
        )
    
    # Filter by batch
    if batch_id:
        query = query.filter(Profile.batch_id == batch_id)
    
    # Filter by date range
    query = query.filter(
        Attendance.day >= start_date,
        Attendance.day <= end_date
    )
    
    # Group by day and status
    query = query.group_by(Attendance.day, Attendance.status).order_by(Attendance.day)
    
    results = query.all()
    
    # Format results by date
    trends_by_date = {}
    for day, status, count in results:
        date_str = day.isoformat()
        if date_str not in trends_by_date:
            trends_by_date[date_str] = {
                'date': date_str,
                'present': 0,
                'absent': 0,
                'late': 0,
                'leave': 0,
                'total': 0
            }
        status_lower = status.lower()
        trends_by_date[date_str][status_lower] = count
        trends_by_date[date_str]['total'] += count
    
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "trends": list(trends_by_date.values())
    }


@router.get("/dashboard/batch-wise")
def get_dashboard_batch_wise(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get attendance statistics grouped by batch.
    
    Query params:
    - start_date: Start date for date range
    - end_date: End date for date range
    
    Returns attendance distribution for each batch.
    
    RBAC:
    - ADMIN: All batches
    - TECHNICAL_LEAD: Only their batches
    """
    from sqlalchemy import func, or_
    from app.models.attendance import Attendance
    from app.models.profile import Profile
    from app.models.batch import Batch
    
    # Base query
    query = db.query(
        Batch.id,
        Batch.name,
        Attendance.status,
        func.count(Attendance.id).label('count')
    ).join(Profile, Attendance.user_id == Profile.id).join(
        Batch, Profile.batch_id == Batch.id
    )
    
    # RBAC: Tech Lead can only see their batches
    if current_user and current_user.role == "TECHNICAL_LEAD":
        query = query.filter(
            or_(
                Batch.first_tech_lead_id == current_user.id,
                Batch.second_tech_lead_id == current_user.id
            )
        )
    
    # Filter by date range
    if start_date:
        query = query.filter(Attendance.day >= start_date)
    if end_date:
        query = query.filter(Attendance.day <= end_date)
    
    # Group by batch and status
    query = query.group_by(Batch.id, Batch.name, Attendance.status)
    
    results = query.all()
    
    # Format results by batch
    batches_data = {}
    for batch_id, batch_name, status, count in results:
        batch_id_str = str(batch_id)
        if batch_id_str not in batches_data:
            batches_data[batch_id_str] = {
                'batch_id': batch_id_str,
                'batch_name': batch_name,
                'present': 0,
                'absent': 0,
                'late': 0,
                'leave': 0,
                'total': 0
            }
        status_lower = status.lower()
        batches_data[batch_id_str][status_lower] = count
        batches_data[batch_id_str]['total'] += count
    
    # Calculate attendance rate for each batch
    for batch_data in batches_data.values():
        total = batch_data['total']
        if total > 0:
            attended = batch_data['present'] + batch_data['late']
            batch_data['attendance_rate'] = round((attended / total) * 100, 2)
        else:
            batch_data['attendance_rate'] = 0.0
    
    return {
        "batches": list(batches_data.values())
    }


@router.get("/dashboard/intern/{intern_id}", response_model=InternAttendanceAnalytics)
def get_dashboard_intern_analytics(
    intern_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get individual intern attendance analytics for dashboard.
    
    Returns:
    - Attendance counts by status
    - Attendance percentage
    - Trend data for charts
    
    RBAC:
    - ADMIN: Any intern
    - TECHNICAL_LEAD: Only interns in their batches
    - INTERN: Only their own data
    """
    # Interns can only see their own analytics
    if current_user.role == "INTERN" and current_user.id != intern_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Interns can only view their own attendance analytics"
        )
    
    return attendance_service.get_intern_attendance_analytics(
        db,
        intern_id,
        start_date=start_date,
        end_date=end_date,
        current_user=current_user
    )


# ============================================================================
# ANALYTICS ENDPOINTS (Legacy - kept for backward compatibility)
# ============================================================================

@router.get("/analytics/distribution", response_model=AttendanceDistribution)
def get_attendance_distribution(
    batch_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get attendance distribution (counts by status) for analytics/dashboard.
    Returns data suitable for pie charts.
    
    Query params:
    - batch_id: Filter by specific batch
    - start_date: Start date for date range
    - end_date: End date for date range
    
    RBAC:
    - ADMIN: All attendance
    - TECHNICAL_LEAD: Only their batches
    """
    return attendance_service.get_attendance_distribution(
        db,
        batch_id=batch_id,
        start_date=start_date,
        end_date=end_date,
        current_user=current_user
    )


@router.get("/analytics/intern/{intern_id}", response_model=InternAttendanceAnalytics)
def get_intern_attendance_analytics(
    intern_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get individual intern attendance analytics.
    
    Returns:
    - Attendance counts by status
    - Attendance percentage
    - Trend data for charts
    
    RBAC:
    - ADMIN: Any intern
    - TECHNICAL_LEAD: Only interns in their batches
    - INTERN: Only their own data
    """
    # Interns can only see their own analytics
    if current_user.role == "INTERN" and current_user.id != intern_id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Interns can only view their own attendance analytics"
        )
    
    return attendance_service.get_intern_attendance_analytics(
        db,
        intern_id,
        start_date=start_date,
        end_date=end_date,
        current_user=current_user
    )


@router.get("/pending", response_model=list[PendingAttendanceIntern])
def get_pending_attendance_interns(
    attendance_date: date,
    batch_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get list of interns for attendance marking.
    Shows which interns already have attendance marked for the specified date.
    
    Query params:
    - attendance_date: Date to check attendance for (required)
    - batch_id: Filter by specific batch
    
    Returns:
    - List of interns with has_attendance flag
    - Interns with has_attendance=true already have attendance for the date
    - Interns with has_attendance=false need attendance marking
    
    RBAC:
    - ADMIN: All interns
    - TECHNICAL_LEAD: Only interns in their batches
    """
    return attendance_service.get_pending_attendance_interns(
        db,
        attendance_date=attendance_date,
        batch_id=batch_id,
        current_user=current_user
    )


@router.get("", response_model=list[AttendanceResponse])
def get_attendance(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID | None = None,
    start: date | None = None,
    end: date | None = None,
    search: str | None = None,
    batch_id: UUID | None = None,
    attendance_date: date | None = None,
    status: str | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get attendance records with role-based access control.
    - ADMIN: Full access to all attendance records
    - TECH_LEAD: Only attendance for interns in their batch
    - INTERN: Only their own attendance records
    
    Query params:
    - search: Search by user name (partial match)
    - batch_id: Filter by batch
    - attendance_date: Filter by specific date
    - status: Filter by status (PRESENT, ABSENT, LEAVE)
    - sort_by: Sort field (date, status, name)
    - order: Sort order (asc, desc)
    """
    # Interns can only see their own attendance
    if current_user.role == "INTERN":
        user_id = current_user.id
    
    return attendance_service.list_attendance(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        start=start,
        end=end,
        search=search,
        batch_id=batch_id,
        attendance_date=attendance_date,
        status=status,
        sort_by=sort_by,
        order=order,
        current_user=current_user,
    )


@router.get("/{attendance_id}", response_model=AttendanceResponse)
def get_attendance_record(
    attendance_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get a single attendance record with enhanced profile and batch data.
    """
    return attendance_service.get_attendance(db, attendance_id)


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def create_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Create attendance record with access control.
    - ADMIN: Can create attendance for any user
    - TECH_LEAD: Can only create attendance for interns in their batch
    - INTERN: Cannot create attendance
    """
    return attendance_service.create_attendance(db, payload, current_user)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: UUID,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update attendance record with access control.
    - ADMIN: Can update any attendance
    - TECH_LEAD: Can only update attendance for interns in their batch
    - INTERN: Cannot update attendance
    """
    return attendance_service.update_attendance(db, attendance_id, payload, current_user)


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """
    Delete attendance record with access control.
    - ADMIN: Can delete any attendance
    - TECH_LEAD: Can only delete attendance for interns in their batch
    - INTERN: Cannot delete attendance
    """
    attendance_service.delete_attendance(db, attendance_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
