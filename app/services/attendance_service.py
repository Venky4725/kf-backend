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
        from sqlalchemy.exc import DataError, IntegrityError
        
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
                
                # Check if intern is in any batch where TL is assigned
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                # Check if TL is assigned to intern's batch (any TL position)
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, target_user.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only mark attendance for interns in their assigned batches"
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
        logger.info(f"Creating new attendance for user {payload.user_id} on {day_value} with status {status_value}")
        
        try:
            new_attendance = self.create(
                db,
                {
                    "user_id": payload.user_id,
                    "day": day_value,
                    "status": status_value,
                },
            )
        except DataError as e:
            # Handle enum constraint violation
            logger.error(f"DataError creating attendance: {e}")
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            if 'attendance_status' in error_msg and 'enum' in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid attendance status '{status_value}'. Database enum needs migration. Valid values: PRESENT, ABSENT, LEAVE, LATE. Please contact administrator."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid data for attendance creation: {error_msg}"
                )
        except IntegrityError as e:
            # Handle other integrity errors
            logger.error(f"IntegrityError creating attendance: {e}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Attendance record already exists for this user and date"
            )
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error creating attendance: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create attendance record. Please try again or contact administrator."
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
        from sqlalchemy.orm import joinedload, contains_eager
        from app.models.profile import Profile
        from app.models.batch import Batch
        
        logger = logging.getLogger(__name__)
        
        # Base query with joins and eager loading using contains_eager to leverage the joins
        # Optimized to load only required columns from Profile and Batch
        query = db.query(Attendance).join(
            Profile, Attendance.user_id == Profile.id
        ).outerjoin(
            Batch, Profile.batch_id == Batch.id
        ).options(
            contains_eager(Attendance.profile).load_only(Profile.id, Profile.name, Profile.email, Profile.batch_id),
            contains_eager(Attendance.profile).contains_eager(Profile.batch).load_only(Batch.id, Batch.name)
        )
        
        # RBAC: Tech Lead can only see their batches
        if current_user and current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if tl_batch_ids:
                query = query.filter(Profile.batch_id.in_(tl_batch_ids))
            else:
                query = query.filter(Profile.id == None)
        
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
        from sqlalchemy.exc import DataError
        
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
                # Check if intern is in any batch where TL is assigned
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                # Check if TL is assigned to intern's batch (any TL position)
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, target_user.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only update attendance for interns in their assigned batches"
                    )
            
            # INTERN cannot update attendance
            elif current_user.role == "INTERN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Interns cannot update attendance records"
                )
        
        # Update the attendance
        try:
            updated = self.update(db, attendance_id, {"status": payload.status})
        except DataError as e:
            # Handle enum constraint violation
            logger.error(f"DataError updating attendance: {e}")
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            if 'attendance_status' in error_msg and 'enum' in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid attendance status '{payload.status}'. Database enum needs migration. Valid values: PRESENT, ABSENT, LEAVE, LATE. Please contact administrator."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid data for attendance update: {error_msg}"
                )
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error updating attendance: {e}", exc_info=True)
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update attendance record. Please try again or contact administrator."
            )
        
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
                # Check if intern is in any batch where TL is assigned
                if target_user.batch_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Intern is not assigned to any batch"
                    )
                
                # Check if TL is assigned to intern's batch (any TL position)
                from app.core.tech_lead_utils import is_tech_lead_for_batch
                if not is_tech_lead_for_batch(db, current_user.id, target_user.batch_id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tech Lead can only delete attendance for interns in their assigned batches"
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
    
    def get_attendance_distribution(
        self,
        db: Session,
        *,
        batch_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        current_user=None,
        tl_batch_ids: list[UUID] | None = None
    ) -> dict:
        """
        Get attendance distribution (counts by status) for analytics.
        Optimized to avoid joins for Admins when batch filtering is not needed.
        """
        import logging
        from sqlalchemy import func
        from app.models.profile import Profile
        
        logger = logging.getLogger(__name__)
        
        # Base query
        query = db.query(
            Attendance.status,
            func.count(Attendance.id).label('count')
        )
        
        # Determine if we need to join with Profile
        needs_profile_join = False
        
        # RBAC: Tech Lead ALWAYS needs profile join to check batches
        if current_user and current_user.role == "TECHNICAL_LEAD":
            needs_profile_join = True
        elif current_user and current_user.role == "INTERN":
            needs_profile_join = False # Intern only needs Attendance table for their own ID
        elif batch_id:
            needs_profile_join = True
            
        if needs_profile_join:
            query = query.join(Profile, Attendance.user_id == Profile.id)
            
            # RBAC filter for TL
            if current_user and current_user.role == "TECHNICAL_LEAD":
                if tl_batch_ids is None:
                    from app.core.tech_lead_utils import get_tech_lead_batch_ids
                    tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
                
                if tl_batch_ids:
                    query = query.filter(Profile.batch_id.in_(tl_batch_ids))
                else:
                    query = query.filter(Profile.id == None)
            
            # Batch filter
            if batch_id:
                query = query.filter(Profile.batch_id == batch_id)
        
        # Intern filter
        if current_user and current_user.role == "INTERN":
            query = query.filter(Attendance.user_id == current_user.id)
        
        # Filter by date range (on Attendance table directly)
        if start_date:
            query = query.filter(Attendance.day >= start_date)
        if end_date:
            query = query.filter(Attendance.day <= end_date)
        
        # Group by status
        query = query.group_by(Attendance.status)
        
        # Execute query
        results = query.all()
        
        # Initialize counts
        distribution = {
            'present_count': 0,
            'absent_count': 0,
            'late_count': 0,
            'leave_count': 0,
            'total_count': 0
        }
        
        # Populate counts
        for status, count in results:
            status_lower = status.lower()
            if status_lower == 'present':
                distribution['present_count'] = count
            elif status_lower == 'absent':
                distribution['absent_count'] = count
            elif status_lower == 'late':
                distribution['late_count'] = count
            elif status_lower == 'leave':
                distribution['leave_count'] = count
            distribution['total_count'] += count
        
        # Calculate percentages
        total = distribution['total_count']
        if total > 0:
            distribution['present_percentage'] = round((distribution['present_count'] / total) * 100, 2)
            distribution['absent_percentage'] = round((distribution['absent_count'] / total) * 100, 2)
            distribution['late_percentage'] = round((distribution['late_count'] / total) * 100, 2)
            distribution['leave_percentage'] = round((distribution['leave_count'] / total) * 100, 2)
        else:
            distribution['present_percentage'] = 0.0
            distribution['absent_percentage'] = 0.0
            distribution['late_percentage'] = 0.0
            distribution['leave_percentage'] = 0.0
        
        return distribution
    
    def get_intern_attendance_analytics(
        self,
        db: Session,
        intern_id: UUID,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        current_user=None
    ) -> dict:
        """
        Get individual intern attendance analytics.
        """
        import logging
        from sqlalchemy import func
        from sqlalchemy.orm import joinedload
        from app.models.profile import Profile
        from app.models.batch import Batch
        from fastapi import HTTPException, status
        
        logger = logging.getLogger(__name__)
        
        # Get intern profile
        intern = db.query(Profile).options(
            joinedload(Profile.batch)
        ).filter(Profile.id == intern_id).first()
        
        if not intern:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intern not found"
            )
        
        # RBAC: Tech Lead can only see interns in their batches
        if current_user and current_user.role == "TECHNICAL_LEAD":
            # Check if intern is in any batch where TL is assigned
            if intern.batch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Intern is not assigned to any batch"
                )
            
            # Check if TL is assigned to intern's batch (any TL position)
            from app.core.tech_lead_utils import is_tech_lead_for_batch
            if not is_tech_lead_for_batch(db, current_user.id, intern.batch_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tech Lead can only view analytics for interns in their assigned batches"
                )
        
        # Base query for counts
        query = db.query(
            Attendance.status,
            func.count(Attendance.id).label('count')
        ).filter(Attendance.user_id == intern_id)
        
        # Filter by date range
        if start_date:
            query = query.filter(Attendance.day >= start_date)
        if end_date:
            query = query.filter(Attendance.day <= end_date)
        
        # Group by status
        results = query.group_by(Attendance.status).all()
        
        # Initialize counts
        analytics = {
            'intern_id': intern_id,
            'intern_name': intern.name,
            'batch_id': intern.batch_id,
            'batch_name': intern.batch.name if intern.batch else None,
            'present_count': 0,
            'absent_count': 0,
            'late_count': 0,
            'leave_count': 0,
            'total_days': 0,
            'attendance_percentage': 0.0,
            'trend': []
        }
        
        # Populate counts
        for status, count in results:
            status_lower = status.lower()
            if status_lower == 'present':
                analytics['present_count'] = count
            elif status_lower == 'absent':
                analytics['absent_count'] = count
            elif status_lower == 'late':
                analytics['late_count'] = count
            elif status_lower == 'leave':
                analytics['leave_count'] = count
            analytics['total_days'] += count
        
        # Calculate attendance percentage (present + late / total)
        total = analytics['total_days']
        if total > 0:
            attended = analytics['present_count'] + analytics['late_count']
            analytics['attendance_percentage'] = round((attended / total) * 100, 2)
        
        # Get trend data (last 30 days or date range)
        trend_query = db.query(
            Attendance.day,
            Attendance.status,
            func.count(Attendance.id).label('count')
        ).filter(Attendance.user_id == intern_id)
        
        if start_date:
            trend_query = trend_query.filter(Attendance.day >= start_date)
        if end_date:
            trend_query = trend_query.filter(Attendance.day <= end_date)
        
        trend_results = trend_query.group_by(Attendance.day, Attendance.status).order_by(Attendance.day).all()
        
        # Group trend by date
        trend_by_date = {}
        for day, status, count in trend_results:
            if day not in trend_by_date:
                trend_by_date[day] = {
                    'date': day.isoformat(),
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'leave': 0,
                    'total': 0
                }
            status_lower = status.lower()
            trend_by_date[day][status_lower] = count
            trend_by_date[day]['total'] += count
        
        analytics['trend'] = list(trend_by_date.values())
        
        return analytics
    
    def get_pending_attendance_interns(
        self,
        db: Session,
        *,
        attendance_date: date,
        batch_id: UUID | None = None,
        current_user=None
    ) -> list:
        """
        Get list of interns who don't have attendance marked for the specified date.
        This is used for the attendance marking interface.
        """
        import logging
        from sqlalchemy.orm import joinedload
        from app.models.profile import Profile
        from app.models.batch import Batch
        
        logger = logging.getLogger(__name__)
        
        # Get all interns
        query = db.query(Profile).filter(Profile.role == "INTERN").options(
            joinedload(Profile.batch)
        )
        
        # RBAC: Tech Lead can only see interns in their batches
        if current_user and current_user.role == "TECHNICAL_LEAD":
            # Filter by batches where TL is assigned (any position: first, second, or third)
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if tl_batch_ids:
                query = query.filter(Profile.batch_id.in_(tl_batch_ids))
            else:
                # Tech lead has no batches assigned, show no interns
                query = query.filter(Profile.id == None)
        
        # Filter by batch if specified
        if batch_id:
            query = query.filter(Profile.batch_id == batch_id)
        
        interns = query.all()
        
        # Get existing attendance for the date
        existing_attendance = db.query(Attendance.user_id).filter(
            Attendance.day == attendance_date
        ).all()
        existing_user_ids = {user_id for (user_id,) in existing_attendance}
        
        # Filter out interns who already have attendance
        pending_interns = []
        for intern in interns:
            has_attendance = intern.id in existing_user_ids
            pending_interns.append({
                'id': intern.id,
                'name': intern.name,
                'email': intern.email,
                'batch_id': intern.batch_id,
                'batch_name': intern.batch.name if intern.batch else None,
                'has_attendance': has_attendance
            })
        
        return pending_interns


attendance_service = AttendanceService()
