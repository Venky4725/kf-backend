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
