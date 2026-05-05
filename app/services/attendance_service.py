from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError, ValidationError

VALID_ATTENDANCE_STATUSES = {"PRESENT", "ABSENT", "LEAVE", "LATE"}


class AttendanceService(CRUDService[Attendance]):
    model = Attendance
    resource_name = "Attendance"
    table_name = "attendance"

    def create_attendance(self, db: Session, payload: AttendanceCreate, current_user=None) -> Attendance:
        import logging
        from fastapi import HTTPException, status
        from app.models.profile import Profile
        
        logger = logging.getLogger(__name__)
        
        # Validate profile exists
        self._ensure_profile_exists(db, payload.user_id)
        
        # Get the target user
        target_user = db.get(Profile, payload.user_id)
        
        # Access control
        if current_user:
            logger.info(f"User {current_user.id} ({current_user.role}) creating attendance for {payload.user_id}")
            
            # ADMIN can create attendance for anyone
            if current_user.role == "ADMIN":
                pass
            
            # TECH_LEAD can only create attendance for interns in their batch
            elif current_user.role == "TECHNICAL_LEAD":
                if current_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead is not assigned to any batch"
                    )
                
                if target_user.role != "INTERN":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only mark attendance for interns"
                    )
                
                if target_user.batch_id != current_user.batch_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only mark attendance for interns in their batch"
                    )
            
            # INTERN cannot create attendance
            elif current_user.role == "INTERN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interns cannot create attendance records"
                )
        
        status_value = self._normalize_status(payload.status)

        # Check for existing attendance on the same day
        existing = (
            db.query(Attendance)
            .filter(Attendance.user_id == payload.user_id, Attendance.day == payload.day)
            .first()
        )
        
        if existing is not None:
            # Update existing attendance instead of throwing error
            logger.info(f"Updating existing attendance {existing.id} for user {payload.user_id} on {payload.day}")
            existing.status = status_value
            db.commit()
            db.refresh(existing)
            return existing

        # Create new attendance record
        logger.info(f"Creating new attendance for user {payload.user_id} on {payload.day}")
        return self.create(
            db,
            {
                "user_id": payload.user_id,
                "day": payload.day,
                "status": status_value,
            },
        )

    def list_attendance(
        self,
        db: Session,
        *,
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
        current_user=None,
    ) -> list[Attendance]:
        import logging
        from sqlalchemy import asc, desc, func, or_
        from app.models.profile import Profile
        from app.models.batch import Batch
        
        logger = logging.getLogger(__name__)
        
        try:
            # Base query with joins for search and filtering
            query = db.query(Attendance).join(
                Profile, Attendance.user_id == Profile.id
            ).outerjoin(
                Batch, Profile.batch_id == Batch.id
            )
            
            # CRITICAL: Tech Lead can only see attendance for their batch
            if current_user and current_user.role == "TECHNICAL_LEAD":
                if current_user.batch_id is None:
                    logger.warning(f"Tech Lead {current_user.id} has no batch assigned")
                    return []  # Tech Lead not assigned to any batch
                query = query.filter(Profile.batch_id == current_user.batch_id)
                logger.info(f"Tech Lead filter applied: batch_id={current_user.batch_id}")
            
            # Filter by user_id
            if user_id:
                query = query.filter(Attendance.user_id == user_id)
            
            # Filter by date range (start/end)
            if start:
                query = query.filter(Attendance.day >= start)
            if end:
                query = query.filter(Attendance.day <= end)
            
            # Filter by specific date
            if attendance_date:
                query = query.filter(Attendance.day == attendance_date)
            
            # Filter by batch_id
            if batch_id:
                query = query.filter(Profile.batch_id == batch_id)
            
            # Filter by status
            if status:
                normalized_status = status.strip().upper()
                if normalized_status in VALID_ATTENDANCE_STATUSES:
                    query = query.filter(Attendance.status == normalized_status)
            
            # Search by user name (case-insensitive partial match)
            if search and search.strip():
                search_term = f"%{search.strip().lower()}%"
                try:
                    query = query.filter(func.lower(Profile.name).like(search_term))
                except Exception as e:
                    logger.error(f"Error applying search filter: {e}")
            
            # Sorting
            VALID_SORT_FIELDS = {"date", "status", "name"}
            if sort_by and sort_by.lower() in VALID_SORT_FIELDS:
                try:
                    order_func = desc if order and order.lower() == "desc" else asc
                    if sort_by.lower() == "date":
                        query = query.order_by(order_func(Attendance.day))
                    elif sort_by.lower() == "status":
                        query = query.order_by(order_func(Attendance.status))
                    elif sort_by.lower() == "name":
                        query = query.order_by(order_func(Profile.name))
                except Exception as e:
                    logger.error(f"Error applying sort: {e}")
                    # Default sorting
                    query = query.order_by(Attendance.day.desc(), Attendance.created_at.desc())
            else:
                # Default sorting
                query = query.order_by(Attendance.day.desc(), Attendance.created_at.desc())
            
            # Apply pagination
            results = query.offset(skip).limit(limit).all()
            
            # Enhance results with user_name and batch_name
            for attendance in results:
                user = db.get(Profile, attendance.user_id)
                if user:
                    attendance.user_name = user.name
                    if user.batch_id:
                        batch = db.get(Batch, user.batch_id)
                        attendance.batch_name = batch.name if batch else None
                    else:
                        attendance.batch_name = None
                else:
                    attendance.user_name = None
                    attendance.batch_name = None
            
            return results
        except Exception as e:
            logger.error(f"Error in list_attendance: {e}")
            return []

    def update_attendance(self, db: Session, attendance_id: UUID, payload: AttendanceUpdate, current_user=None) -> Attendance:
        import logging
        from fastapi import HTTPException, status
        from app.models.profile import Profile
        
        logger = logging.getLogger(__name__)
        
        # Get the attendance record
        attendance = self.get(db, attendance_id)
        
        # Get the target user
        target_user = db.get(Profile, attendance.user_id)
        
        # Access control
        if current_user:
            logger.info(f"User {current_user.id} ({current_user.role}) updating attendance {attendance_id}")
            
            # ADMIN can update any attendance
            if current_user.role == "ADMIN":
                pass
            
            # TECH_LEAD can only update attendance for interns in their batch
            elif current_user.role == "TECHNICAL_LEAD":
                if current_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead is not assigned to any batch"
                    )
                
                if target_user.batch_id != current_user.batch_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only update attendance for interns in their batch"
                    )
            
            # INTERN cannot update attendance
            elif current_user.role == "INTERN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interns cannot update attendance records"
                )
        
        return self.update(db, attendance_id, {"status": self._normalize_status(payload.status)})
    
    def delete_attendance(self, db: Session, attendance_id: UUID, current_user=None) -> None:
        import logging
        from fastapi import HTTPException, status
        from app.models.profile import Profile
        
        logger = logging.getLogger(__name__)
        
        # Get the attendance record
        attendance = self.get(db, attendance_id)
        
        # Get the target user
        target_user = db.get(Profile, attendance.user_id)
        
        # Access control
        if current_user:
            logger.info(f"User {current_user.id} ({current_user.role}) deleting attendance {attendance_id}")
            
            # ADMIN can delete any attendance
            if current_user.role == "ADMIN":
                pass
            
            # TECH_LEAD can only delete attendance for interns in their batch
            elif current_user.role == "TECHNICAL_LEAD":
                if current_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead is not assigned to any batch"
                    )
                
                if target_user.batch_id != current_user.batch_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete attendance for interns in their batch"
                    )
            
            # INTERN cannot delete attendance
            elif current_user.role == "INTERN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interns cannot delete attendance records"
                )
        
        self.delete(db, attendance_id)

    def _normalize_status(self, status: str) -> str:
        normalized = status.strip().upper()
        if normalized not in VALID_ATTENDANCE_STATUSES:
            raise ValidationError(
                f"Attendance status must be one of: {', '.join(sorted(VALID_ATTENDANCE_STATUSES))}."
            )
        return normalized

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        from app.models.profile import Profile

        if db.get(Profile, profile_id) is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")


attendance_service = AttendanceService()
