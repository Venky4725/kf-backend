# app/routers/attendance.py

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.attendance import AttendanceCreate, AttendanceResponse, AttendanceUpdate
from app.services.attendance_service import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


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
):
    return attendance_service.get(db, attendance_id)


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def create_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
):
    return attendance_service.create_attendance(db, payload)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: UUID,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
):
    return attendance_service.update_attendance(db, attendance_id, payload)


@router.delete("/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(
    attendance_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    attendance_service.delete(db, attendance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
