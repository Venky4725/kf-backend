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
                
                from app.models.batch import Batch
                batch = db.query(Batch).filter(
                    Batch.id == target_user.batch_id,
                    Batch.team_lead_id == current_user.id
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
            
            # Re-query with joinedload to ensure relationships are loaded
            from sqlalchemy.orm import joinedload
            existing = db.query(Attendance).options(
                joinedload(Attendance.profile).joinedload(Profile.batch)
            ).filter(Attendance.id == existing.id).first()
            
            # Populate user_name and batch_name for response using relationships
            if existing and existing.profile:
                existing.user_name = existing.profile.name
                if existing.profile.batch:
                    existing.batch_name = existing.profile.batch.name
                    logger.info(f"Updated attendance with batch_name: {existing.batch_name}")
                else:
                    existing.batch_name = None
                    logger.warning(f"No batch found for user {existing.profile.id}")
            else:
                existing.user_name = None
                existing.batch_name = None
                logger.warning(f"Profile not loaded for existing attendance")
            
            return existing

        # Create new attendance record
        logger.info(f"Creating new attendance for user {payload.user_id} on {payload.day}")
        new_attendance = self.create(
            db,
            {
                "user_id": payload.user_id,
                "day": payload.day,
                "status": status_value,
            },
        )
        
        # Refresh with explicit relationship loading
        from sqlalchemy.orm import joinedload
        db.refresh(new_attendance)
        
        # Re-query with joinedload to ensure relationships are loaded
        new_attendance = db.query(Attendance).options(
            joinedload(Attendance.profile).joinedload(Profile.batch)
        ).filter(Attendance.id == new_attendance.id).first()
        
        # Populate user_name and batch_name for response using relationships
        if new_attendance and new_attendance.profile:
            new_attendance.user_name = new_attendance.profile.name
            if new_attendance.profile.batch:
                new_attendance.batch_name = new_attendance.profile.batch.name
                logger.info(f"Created attendance with batch_name: {new_attendance.batch_name}")
            else:
                new_attendance.batch_name = None
                logger.warning(f"No batch found for user {new_attendance.profile.id}")
        else:
            new_attendance.user_name = None
            new_attendance.batch_name = None
            logger.warning(f"Profile not loaded for new attendance")
        
        return new_attendance

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
        
        # Base query with INNER joins for filtering AND eager loading for relationships
        # Using join (not outerjoin) ensures only interns WITH batches are returned
        query = db.query(Attendance).join(
            Profile, Attendance.user_id == Profile.id
        ).join(
            Batch, Profile.batch_id == Batch.id  # INNER JOIN - excludes NULL batches
        ).options(
            # CRITICAL: Use joinedload to populate relationships
            joinedload(Attendance.profile).joinedload(Profile.batch)
        )
        
        # CRITICAL: Tech Lead can only see attendance for interns in batches they lead
        if current_user and current_user.role == "TECHNICAL_LEAD":
            # Filter by batches where this Tech Lead is assigned
            query = query.filter(Batch.team_lead_id == current_user.id)
            logger.info(f"Tech Lead filter applied: team_lead_id={current_user.id}")
            
            # Debug: Log batches assigned to this Tech Lead
            tech_lead_batches = db.query(Batch).filter(Batch.team_lead_id == current_user.id).all()
            batch_ids = [str(b.id) for b in tech_lead_batches]
            logger.info(f"Tech Lead {current_user.id} leads batches: {batch_ids}")
            
            # Check if Tech Lead has any batches
            if len(tech_lead_batches) == 0:
                logger.warning(f"Tech Lead {current_user.id} is not assigned to any batches")
                return []  # Tech Lead not assigned to any batch - this is valid, not an error
        
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
        
        # Enhance results with user_name and batch_name using relationships
        for attendance in results:
            # Use the relationship to access profile (should be loaded via joinedload)
            if attendance.profile:
                attendance.user_name = attendance.profile.name
                logger.info(f"Attendance {attendance.id}: user_name={attendance.profile.name}, batch_id={attendance.profile.batch_id}")
                
                # Use the relationship to access batch through profile (should be loaded via joinedload)
                if attendance.profile.batch:
                    attendance.batch_name = attendance.profile.batch.name
                    logger.info(f"Attendance {attendance.id}: batch_name={attendance.profile.batch.name}")
                else:
                    attendance.batch_name = None
                    if attendance.profile.batch_id:
                        logger.warning(f"Batch relationship not loaded for user {attendance.profile.id}, batch_id={attendance.profile.batch_id}")
                    else:
                        logger.info(f"User {attendance.profile.id} has no batch_id")
            else:
                attendance.user_name = None
                attendance.batch_name = None
                logger.warning(f"Profile relationship not loaded for attendance {attendance.id}, user_id={attendance.user_id}")
        
        return results

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
                # Check if intern is in a batch led by this Tech Lead
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                from app.models.batch import Batch
                batch = db.query(Batch).filter(
                    Batch.id == target_user.batch_id,
                    Batch.team_lead_id == current_user.id
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
                # Check if intern is in a batch led by this Tech Lead
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                from app.models.batch import Batch
                batch = db.query(Batch).filter(
                    Batch.id == target_user.batch_id,
                    Batch.team_lead_id == current_user.id
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
