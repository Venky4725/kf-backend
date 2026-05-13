from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError, ValidationError

# CRITICAL: Database enum values are UPPERCASE
VALID_ATTENDANCE_STATUSES = {"PRESENT", "ABSENT", "LEAVE", "LATE"}


class AttendanceService(CRUDService[Attendance]):
    model = Attendance
    resource_name = "Attendance"
    table_name = "attendance"

    def create_attendance(self, db: Session, payload: AttendanceCreate, current_user=None) -> Attendance:
        import logging
        from fastapi import HTTPException, status
        from app.models.profile import Profile
        from app.models.batch import Batch
        from sqlalchemy.orm import joinedload
        
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
                if target_user.role != "INTERN":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only mark attendance for interns"
                    )
                
                # Check if intern is in a batch led by this Tech Lead
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                batch = db.query(Batch).filter(
                    Batch.id == target_user.batch_id,
                    or_(
                        Batch.first_tech_lead_id == current_user.id,
                        Batch.second_tech_lead_id == current_user.id
                    )
                ).first()
                
                if not batch:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only mark attendance for interns in batches they lead"
                    )
            
            # INTERN cannot create attendance
            elif current_user.role == "INTERN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interns cannot create attendance records"
                )
        
        # Status is already normalized by the validator
        status_value = payload.status
        
        # Get the day value from the payload
        day_value = payload.day

        # Check for existing attendance on the same day
        existing = (
            db.query(Attendance)
            .filter(Attendance.user_id == payload.user_id, Attendance.day == day_value)
            .first()
        )
        
        if existing is not None:
            # Update existing attendance instead of throwing error
            logger.info(f"Updating existing attendance {existing.id} for user {payload.user_id} on {payload.day}")
            existing.status = status_value
            db.commit()
            db.refresh(existing)
            
            # Re-query with joinedload to ensure relationships are loaded
            existing = db.query(Attendance).options(
                joinedload(Attendance.profile).joinedload(Profile.batch)
            ).filter(Attendance.id == existing.id).first()
            
            # Populate enhanced fields for response
            return self._enhance_attendance_response(existing)

        # Create new attendance record
        logger.info(f"Creating new attendance for user {payload.user_id} on {day_value}")
        new_attendance = self.create(
            db,
            {
                "user_id": payload.user_id,
                "day": day_value,
                "status": status_value,
            },
        )
        
        # Re-query with joinedload to ensure relationships are loaded
        new_attendance = db.query(Attendance).options(
            joinedload(Attendance.profile).joinedload(Profile.batch)
        ).filter(Attendance.id == new_attendance.id).first()
        
        # Populate enhanced fields for response
        return self._enhance_attendance_response(new_attendance)

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
        from sqlalchemy import asc, desc, func
        from sqlalchemy.orm import joinedload
        from app.models.profile import Profile
        from app.models.batch import Batch
        
        logger = logging.getLogger(__name__)
        
        # Log the request
        if current_user:
            logger.info(f"list_attendance called by {current_user.id} ({current_user.role})")
        
        # Base query with joins and eager loading
        query = db.query(Attendance).join(
            Profile, Attendance.user_id == Profile.id
        ).outerjoin(
            Batch, Profile.batch_id == Batch.id
        ).options(
            # CRITICAL: Use joinedload to populate relationships
            joinedload(Attendance.profile).joinedload(Profile.batch)
        )
        
        # CRITICAL: Tech Lead can only see attendance for interns in batches they lead
        if current_user and current_user.role == "TECHNICAL_LEAD":
            # Filter by batches where this Tech Lead is assigned (first or second)
            query = query.filter(
                or_(
                    Batch.first_tech_lead_id == current_user.id,
                    Batch.second_tech_lead_id == current_user.id
                )
            )
            logger.info(f"Tech Lead filter applied: user_id={current_user.id}")
        
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
            normalized_status = status.strip().upper()  # UPPERCASE to match database enum
            if normalized_status in VALID_ATTENDANCE_STATUSES:
                query = query.filter(Attendance.status == normalized_status)
        
        # Search by user name (case-insensitive partial match)
        if search and search.strip():
            search_term = f"%{search.strip().lower()}%"
            query = query.filter(func.lower(Profile.name).like(search_term))
        
        # Sorting
        VALID_SORT_FIELDS = {"date", "status", "name"}
        if sort_by and sort_by.lower() in VALID_SORT_FIELDS:
            order_func = desc if order and order.lower() == "desc" else asc
            if sort_by.lower() == "date":
                query = query.order_by(order_func(Attendance.day))
            elif sort_by.lower() == "status":
                query = query.order_by(order_func(Attendance.status))
            elif sort_by.lower() == "name":
                query = query.order_by(order_func(Profile.name))
        else:
            # Default sorting
            query = query.order_by(Attendance.day.desc(), Attendance.created_at.desc())
        
        # Apply pagination
        results = query.offset(skip).limit(limit).all()
        
        # Enhance results with profile data
        for attendance in results:
            self._enhance_attendance_response(attendance)
        
        return results

    def update_attendance(self, db: Session, attendance_id: UUID, payload: AttendanceUpdate, current_user=None) -> Attendance:
        import logging
        from fastapi import HTTPException, status
        from app.models.profile import Profile
        from app.models.batch import Batch
        from sqlalchemy.orm import joinedload
        
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
                # Check if intern is in a batch led by this Tech Lead
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                batch = db.query(Batch).filter(
                    Batch.id == target_user.batch_id,
                    or_(
                        Batch.first_tech_lead_id == current_user.id,
                        Batch.second_tech_lead_id == current_user.id
                    )
                ).first()
                
                if not batch:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only update attendance for interns in batches they lead"
                    )
            
            # INTERN cannot update attendance
            elif current_user.role == "INTERN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interns cannot update attendance records"
                )
        
        # Update the attendance
        updated = self.update(db, attendance_id, {"status": payload.status})
        
        # Re-query with joinedload to ensure relationships are loaded
        updated = db.query(Attendance).options(
            joinedload(Attendance.profile).joinedload(Profile.batch)
        ).filter(Attendance.id == attendance_id).first()
        
        # Populate enhanced fields for response
        return self._enhance_attendance_response(updated)
    
    def delete_attendance(self, db: Session, attendance_id: UUID, current_user=None) -> None:
        import logging
        from fastapi import HTTPException, status
        from app.models.profile import Profile
        from app.models.batch import Batch
        
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
                # Check if intern is in a batch led by this Tech Lead
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                batch = db.query(Batch).filter(
                    Batch.id == target_user.batch_id,
                    or_(
                        Batch.first_tech_lead_id == current_user.id,
                        Batch.second_tech_lead_id == current_user.id
                    )
                ).first()
                
                if not batch:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete attendance for interns in batches they lead"
                    )
            
            # INTERN cannot delete attendance
            elif current_user.role == "INTERN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interns cannot delete attendance records"
                )
        
        self.delete(db, attendance_id)
    
    def get_attendance(self, db: Session, attendance_id: UUID) -> Attendance:
        """
        Get a single attendance record with enhanced profile and batch data.
        """
        from sqlalchemy.orm import joinedload
        from app.models.profile import Profile
        
        # Query with joinedload to ensure relationships are loaded
        attendance = db.query(Attendance).options(
            joinedload(Attendance.profile).joinedload(Profile.batch)
        ).filter(Attendance.id == attendance_id).first()
        
        if not attendance:
            raise ConflictError(f"Attendance '{attendance_id}' not found.")
        
        # Populate enhanced fields for response
        return self._enhance_attendance_response(attendance)

    def _normalize_status(self, status: str) -> str:
        """Normalize status to UPPERCASE to match PostgreSQL enum"""
        normalized = status.strip().upper()  # UPPERCASE to match database enum
        if normalized not in VALID_ATTENDANCE_STATUSES:
            raise ValidationError(
                f"Attendance status must be one of: {', '.join(sorted(VALID_ATTENDANCE_STATUSES))}."
            )
        return normalized

    def _ensure_profile_exists(self, db: Session, profile_id: UUID) -> None:
        from app.models.profile import Profile

        if db.get(Profile, profile_id) is None:
            raise ConflictError(f"Profile '{profile_id}' does not exist.")
    
    def _enhance_attendance_response(self, attendance: Attendance) -> Attendance:
        """
        Enhance attendance object with profile and batch data for frontend display.
        This ensures the frontend receives proper user names and batch information.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if attendance and attendance.profile:
            # Set user information
            attendance.user_name = attendance.profile.name
            attendance.user_email = attendance.profile.email
            attendance.batch_id = attendance.profile.batch_id
            
            # Set batch information if available
            if attendance.profile.batch:
                attendance.batch_name = attendance.profile.batch.name
                logger.debug(f"Enhanced attendance {attendance.id} with batch_name: {attendance.batch_name}")
            else:
                attendance.batch_name = None
                if attendance.profile.batch_id:
                    logger.warning(f"Batch relationship not loaded for user {attendance.profile.id}")
        else:
            # Set defaults if profile not loaded
            attendance.user_name = None
            attendance.user_email = None
            attendance.batch_id = None
            attendance.batch_name = None
            logger.warning(f"Profile not loaded for attendance {attendance.id}")
        
        return attendance


attendance_service = AttendanceService()
