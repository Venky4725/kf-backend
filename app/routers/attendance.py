# app/routers/attendance.py

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

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
    db: Session = Depends(get_db),
):
    return attendance_service.list_attendance(db, skip=skip, limit=limit, user_id=user_id, start=start, end=end)


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
