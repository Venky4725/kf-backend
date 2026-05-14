from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from app.core.security import hash_password
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate
from app.services.base import CRUDService
from app.services.exceptions import ConflictError, ValidationError

VALID_PROFILE_ROLES = {"ADMIN", "TECHNICAL_LEAD", "INTERN"}

# Default password for new users
DEFAULT_PASSWORD = "Welcome@123"

# REMOVED: Deprecated function - use app.core.tech_lead_utils.is_tech_lead_for_batch instead
# Technical Lead batch assignments are now managed via Batch table (first/second/third_tech_lead_id)
# NOT via Profile.batch_id


class ProfileService(CRUDService[Profile]):
    model = Profile
    resource_name = "Profile"
    table_name = "profiles"

    def create_profile(self, db: Session, payload: ProfileCreate, current_user=None) -> Profile:
        from sqlalchemy import func
        from app.models.batch import Batch
        import logging
        logger = logging.getLogger(__name__)
        
        # Role is already validated and normalized to uppercase in schema
        role = payload.role
        logger.info(f"Creating profile with role: {role}")
        
        # Handle batch assignment based on role
        batch_id = None
        
        if role == "INTERN":
            # Interns MUST have either batch_id or batch_name (validated in schema)
            if payload.batch_id:
                # Form-based creation: batch_id provided directly
                logger.info(f"Creating INTERN with batch_id: {payload.batch_id}")
                batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
                
                if not batch:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=400,
                        detail=f"Batch with id '{payload.batch_id}' does not exist"
                    )
                
                batch_id = batch.id
                logger.info(f"Found batch: {batch.name} (ID: {batch.id})")
                
            elif payload.batch_name:
                # CSV upload: batch_name provided, lookup or create
                batch_name = payload.batch_name.strip()
                logger.info(f"Creating INTERN with batch_name: {batch_name}")
                
                # Lookup batch by name (case-insensitive)
                batch = db.query(Batch).filter(
                    func.lower(Batch.name) == batch_name.lower()
                ).first()
                
                # Create batch if it doesn't exist
                if not batch:
                    from datetime import datetime
                    logger.info(f"Batch '{batch_name}' not found, creating new batch")
                    batch = Batch(
                        name=batch_name,
                        tech_stack="General",  # Default tech stack for auto-created batches
                        start_date=datetime.utcnow().date(),  # Set to current date
                        first_tech_lead_id=current_user.id if current_user and current_user.role == "TECHNICAL_LEAD" else None,
                        second_tech_lead_id=None
                    )
                    db.add(batch)
                    db.commit()  # CRITICAL: Commit batch immediately to ensure it persists
                    db.refresh(batch)  # Refresh to get the ID
                    logger.info(f"Created new batch: {batch.name} (ID: {batch.id})")
                else:
                    logger.info(f"Found existing batch: {batch.name} (ID: {batch.id})")
                
                batch_id = batch.id
                logger.info(f"Assigning INTERN to batch_id: {batch_id}")
        
        elif role == "TECHNICAL_LEAD":
            # TECHNICAL_LEAD should NOT have batch_id set in Profile table
            # TL assignments are managed via Batch table (first/second/third_tech_lead_id)
            batch_id = None
            logger.info(f"Creating TECHNICAL_LEAD without batch_id (assignments managed via Batch table)")
        
        else:
            # ADMIN does not require batch (and typically shouldn't have one)
            if payload.batch_id:
                logger.warning(f"ADMIN role should not have batch_id, ignoring provided value")
            batch_id = None
            logger.info(f"Creating ADMIN without batch assignment")

        # Generate password hash for default password
        password_hash = hash_password(DEFAULT_PASSWORD)
        
        # Normalize email
        normalized_email = payload.email.lower().strip()
        
        # Check if email already exists
        existing = db.query(Profile).filter(Profile.email == normalized_email).first()
        if existing:
            raise ConflictError(f"A profile with email '{normalized_email}' already exists (Name: {existing.name}, Role: {existing.role}).")

        logger.info(f"Creating profile: {payload.name} ({role}) with batch_id={batch_id}")
        return self.create(
            db,
            {
                "id": uuid4(),
                "name": payload.name.strip(),
                "email": normalized_email,
                "role": role,
                "tech_stack": payload.tech_stack,
                "batch_id": batch_id,
                "password_hash": password_hash,
                "must_change_password": True,
                "is_active": True,
            },
        )

    def list_profiles(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        role: str | None = None,
        batch_id: UUID | None = None,
        search_name: str | None = None,
        search_email: str | None = None,
        tech_stack: str | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        is_active: bool | None = None,
        current_user=None,
    ) -> list[Profile]:
        from app.models.batch import Batch
        from sqlalchemy import asc, desc
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Log the request
        if current_user:
            logger.info(f"list_profiles called by {current_user.id} ({current_user.role})")
        
        # Base query
        query = db.query(Profile)
        
        # Determine if we need to join Batch table
        needs_batch_join = (
            (current_user and current_user.role == "TECHNICAL_LEAD") or
            (sort_by and sort_by.lower() == "batch")
        )
        
        # Apply JOIN if needed (only once)
        if needs_batch_join:
            query = query.join(Batch, Profile.batch_id == Batch.id)
            logger.info("Batch table joined")
        
        # RBAC: Tech Lead can only see interns in batches they lead
        if current_user and current_user.role == "TECHNICAL_LEAD":
            # Filter by interns in batches where TL is assigned (any position)
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if tl_batch_ids:
                query = query.filter(
                    Profile.role == "INTERN",
                    Profile.batch_id.in_(tl_batch_ids)
                )
                logger.info(f"Tech Lead filter applied: only interns in batches {tl_batch_ids}")
            else:
                # Tech lead has no batches assigned, show no interns
                query = query.filter(Profile.id == None)  # Returns empty result
                logger.info("Tech Lead has no assigned batches, showing no interns")
        
        elif current_user and current_user.role == "INTERN":
            # Interns can only see their own profile
            query = query.filter(Profile.id == current_user.id)
            logger.info("Intern filter applied: own profile only")
        
        # Apply is_active filter
        if is_active is not None:
            query = query.filter(Profile.is_active == is_active)
        else:
            # Default: only show active profiles
            query = query.filter(Profile.is_active == True)
        
        # Apply role filter (skip if Tech Lead already filtered by INTERN)
        if role and (not current_user or current_user.role != "TECHNICAL_LEAD"):
            query = query.filter(Profile.role == role.strip().upper())
        
        # Apply batch_id filter
        if batch_id:
            query = query.filter(Profile.batch_id == batch_id)
        
        # Apply search filters
        if search_name:
            query = query.filter(Profile.name.ilike(f"%{search_name}%"))
        
        if search_email:
            query = query.filter(Profile.email.ilike(f"%{search_email}%"))
        
        if tech_stack:
            query = query.filter(Profile.tech_stack.ilike(tech_stack))
        
        # Apply sorting
        VALID_SORT_FIELDS = {"name", "email", "tech_stack", "batch"}
        
        if sort_by and sort_by.lower() in VALID_SORT_FIELDS:
            sort_field = sort_by.lower()
            order_func = asc if sort_order and sort_order.lower() == "asc" else desc
            
            if sort_field == "batch":
                query = query.order_by(order_func(Batch.name))
            elif sort_field == "name":
                query = query.order_by(order_func(Profile.name))
            elif sort_field == "email":
                query = query.order_by(order_func(Profile.email))
            elif sort_field == "tech_stack":
                query = query.order_by(order_func(Profile.tech_stack))
        else:
            # Default sorting
            query = query.order_by(Profile.created_at.desc())
        
        # Apply pagination and return
        return query.offset(skip).limit(limit).all()

    def update_profile(self, db: Session, profile_id: UUID, payload: ProfileUpdate, current_user=None) -> Profile:
        import logging
        logger = logging.getLogger(__name__)
        
        # Log incoming request
        logger.info(f"Updating profile {profile_id} with payload: {payload.model_dump(exclude_unset=True)}")
        
        # Get the existing profile first
        existing_profile = self.get(db, profile_id)
        logger.info(f"Existing profile: name={existing_profile.name}, email={existing_profile.email}, tech_stack={existing_profile.tech_stack}, batch_id={existing_profile.batch_id}")
        
        # Access control
        if current_user:
            logger.info(f"Current user: {current_user.id} ({current_user.role})")
            # ADMIN can update any profile
            if current_user.role == "ADMIN":
                logger.info("Admin access granted")
                pass
            # TECHNICAL_LEAD can only update their own profile or interns in their batch
            elif current_user.role == "TECHNICAL_LEAD":
                # Tech Lead can update their own profile
                if existing_profile.id == current_user.id:
                    logger.info("Tech Lead updating own profile")
                    pass
                # Tech Lead can update interns in their batch (ALLOW BATCH CHANGE)
                elif existing_profile.role == "INTERN":
                    from app.core.tech_lead_utils import is_tech_lead_for_batch, get_tech_lead_batch_ids
                    
                    # Check if intern is currently in any batch where TL is assigned
                    if existing_profile.batch_id:
                        if is_tech_lead_for_batch(db, current_user.id, existing_profile.batch_id):
                            logger.info(f"Tech Lead updating intern in their assigned batch (batch_id: {existing_profile.batch_id})")
                            pass
                        # Also allow if Tech Lead is assigning intern TO one of their batches
                        elif "batch_id" in payload.model_dump(exclude_unset=True):
                            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
                            if payload.batch_id in tl_batch_ids:
                                logger.info(f"Tech Lead assigning intern to their batch (batch_id: {payload.batch_id})")
                                pass
                            else:
                                logger.warning(f"Tech Lead {current_user.id} attempted to update intern {profile_id} not in their batches")
                                from fastapi import HTTPException, status as http_status
                                raise HTTPException(
                                    status_code=http_status.HTTP_403_FORBIDDEN,
                                    detail="You can only update interns in your assigned batches"
                                )
                        else:
                            logger.warning(f"Tech Lead {current_user.id} attempted to update intern {profile_id} not in their batches")
                            from fastapi import HTTPException, status as http_status
                            raise HTTPException(
                                status_code=http_status.HTTP_403_FORBIDDEN,
                                detail="You can only update interns in your assigned batches"
                            )
                    else:
                        # Intern has no batch - allow TL to assign to their batch
                        if "batch_id" in payload.model_dump(exclude_unset=True):
                            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
                            if payload.batch_id in tl_batch_ids:
                                logger.info(f"Tech Lead assigning unassigned intern to their batch")
                                pass
                            else:
                                from fastapi import HTTPException, status as http_status
                                raise HTTPException(
                                    status_code=http_status.HTTP_403_FORBIDDEN,
                                    detail="You can only assign interns to your assigned batches"
                                )
                        else:
                            from fastapi import HTTPException, status as http_status
                            raise HTTPException(
                                status_code=http_status.HTTP_403_FORBIDDEN,
                                detail="You can only update interns in your assigned batches"
                            )
                else:
                    logger.warning(f"Tech Lead {current_user.id} attempted to update non-intern profile {profile_id}")
                    from fastapi import HTTPException, status as http_status
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="You can only update your own profile or interns in your batch"
                    )
            # INTERN can only update their own profile
            elif current_user.role == "INTERN":
                if existing_profile.id != current_user.id:
                    logger.warning(f"Intern {current_user.id} attempted to update another profile {profile_id}")
                    from fastapi import HTTPException, status as http_status
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail="You can only update your own profile"
                    )
                else:
                    logger.info("Intern updating own profile")
        
        updates = payload.model_dump(exclude_unset=True)
        logger.info(f"Updates to apply: {updates}")
        
        # Validate batch exists if being updated
        if "batch_id" in updates and updates["batch_id"] is not None:
            logger.info(f"Validating batch_id: {updates['batch_id']}")
            self._ensure_batch_exists(db, updates["batch_id"])
            logger.info(f"Batch validation passed for batch_id: {updates['batch_id']}")
        
        # Normalize name if being updated
        if "name" in updates and updates["name"] is not None:
            original_name = updates["name"]
            updates["name"] = updates["name"].strip()
            logger.info(f"Normalized name: '{original_name}' -> '{updates['name']}'")
        
        # Handle email update with uniqueness check
        if "email" in updates and updates["email"] is not None:
            normalized_email = updates["email"].lower().strip()
            logger.info(f"Normalizing email: '{updates['email']}' -> '{normalized_email}'")
            
            # Only check for duplicates if email is actually changing
            if normalized_email != existing_profile.email:
                logger.info(f"Email is changing from '{existing_profile.email}' to '{normalized_email}', checking for duplicates")
                existing_with_email = db.query(Profile).filter(
                    Profile.email == normalized_email,
                    Profile.id != profile_id
                ).first()
                
                if existing_with_email:
                    logger.error(f"Email '{normalized_email}' already in use by profile {existing_with_email.id}")
                    raise ConflictError(
                        f"Email '{normalized_email}' is already in use by another profile "
                        f"(Name: {existing_with_email.name}, Role: {existing_with_email.role})."
                    )
            else:
                logger.info("Email unchanged, skipping duplicate check")
            
            updates["email"] = normalized_email
        
        logger.info(f"Calling base update with: {updates}")
        
        try:
            updated_profile = self.update(db, profile_id, updates)
        except IntegrityError as e:
            # Log the full error for debugging
            logger.error(f"IntegrityError during profile update: {e}")
            logger.error(f"Original error: {e.orig}")
            db.rollback()
            
            # Parse the error to provide helpful message
            error_msg = str(e.orig).lower() if hasattr(e, 'orig') else str(e).lower()
            
            if 'unique' in error_msg and 'email' in error_msg:
                raise ConflictError(f"Email address is already in use by another profile.")
            elif 'unique' in error_msg and 'batch' in error_msg:
                raise ConflictError(f"This batch assignment conflicts with existing data.")
            elif 'foreign key' in error_msg:
                raise ConflictError(f"Referenced batch or resource does not exist.")
            else:
                # Generic integrity error
                raise ConflictError(f"Database constraint violation: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error during profile update: {e}", exc_info=True)
            db.rollback()
            raise
        
        logger.info(f"Profile updated successfully: name={updated_profile.name}, email={updated_profile.email}, tech_stack={updated_profile.tech_stack}, batch_id={updated_profile.batch_id}")
        
        return updated_profile

    def delete_profile(self, db: Session, profile_id: UUID) -> None:
        """
        Delete a profile with proper dependency handling.
        For Technical Leads: unassigns from batches before deletion.
        For all profiles: checks for blocking dependencies.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get the profile
        profile = self.get(db, profile_id)
        logger.info(f"Attempting to delete profile: {profile.name} ({profile.role})")
        
        # Import models here to avoid circular imports
        from app.models.batch import Batch
        from app.models.evaluation import Evaluation
        from app.models.submission import Submission
        from app.models.notification import Notification
        
        # Check dependencies and provide detailed error messages
        dependencies = []
        
        # Check if TL is assigned to batches
        if profile.role == "TECHNICAL_LEAD":
            assigned_batches = db.query(Batch).filter(
                or_(
                    Batch.first_tech_lead_id == profile_id,
                    Batch.second_tech_lead_id == profile_id,
                    Batch.third_tech_lead_id == profile_id
                )
            ).all()
            if assigned_batches:
                batch_names = [b.name for b in assigned_batches]
                dependencies.append(f"assigned as Team Lead to {len(assigned_batches)} batch(es): {', '.join(batch_names)}")
                logger.info(f"Found {len(assigned_batches)} batches assigned to TL")
        
        # Check if profile has evaluations (as reviewer)
        try:
            evaluations_count = db.query(Evaluation).filter(Evaluation.reviewed_by == profile_id).count()
            if evaluations_count > 0:
                dependencies.append(f"has {evaluations_count} evaluation(s) as reviewer")
                logger.info(f"Found {evaluations_count} evaluations")
        except Exception as e:
            logger.warning(f"Could not check evaluations: {e}")
        
        # Check if profile has submissions
        try:
            submissions_count = db.query(Submission).filter(Submission.submitted_by == profile_id).count()
            if submissions_count > 0:
                dependencies.append(f"has {submissions_count} submission(s)")
                logger.info(f"Found {submissions_count} submissions")
        except Exception as e:
            logger.warning(f"Could not check submissions: {e}")
        
        # Check if profile has notifications
        try:
            notifications_count = db.query(Notification).filter(Notification.user_id == profile_id).count()
            if notifications_count > 0:
                dependencies.append(f"has {notifications_count} notification(s)")
                logger.info(f"Found {notifications_count} notifications")
        except Exception as e:
            logger.warning(f"Could not check notifications: {e}")
        
        # If there are dependencies, provide detailed error
        if dependencies:
            dependency_list = "; ".join(dependencies)
            error_msg = (
                f"Cannot delete {profile.name} ({profile.role}). "
                f"This profile {dependency_list}. "
                f"Please remove these dependencies first or use deactivation instead."
            )
            logger.error(error_msg)
            raise ConflictError(error_msg)
        
        # If TL has no dependencies, unassign from batches (safety check)
        if profile.role == "TECHNICAL_LEAD":
            # Unassign from all three TL positions
            updated_first = db.query(Batch).filter(Batch.first_tech_lead_id == profile_id).update({"first_tech_lead_id": None})
            updated_second = db.query(Batch).filter(Batch.second_tech_lead_id == profile_id).update({"second_tech_lead_id": None})
            updated_third = db.query(Batch).filter(Batch.third_tech_lead_id == profile_id).update({"third_tech_lead_id": None})
            logger.info(f"Unassigned TL from {updated_first + updated_second + updated_third} batches")
            db.flush()
        
        # Add audit log
        try:
            from app.services.audit import add_audit_log
            add_audit_log(db, action="DELETE", table_name=self.table_name, record_id=profile_id)
        except Exception as e:
            logger.warning(f"Could not add audit log: {e}")
        
        # Now safe to delete
        try:
            db.delete(profile)
            db.commit()
            logger.info(f"Successfully deleted profile: {profile.name}")
        except IntegrityError as exc:
            db.rollback()
            logger.error(f"IntegrityError during delete: {exc}")
            # Provide detailed error message
            detail = str(exc.orig).lower() if exc.orig else str(exc).lower()
            if "foreign key" in detail:
                raise ConflictError(
                    f"Cannot delete {profile.name}. This profile is still referenced by other records. "
                    f"Please remove all dependencies first."
                )
            raise ConflictError(f"Unable to delete profile due to database constraint: {detail}")
        except Exception as exc:
            db.rollback()
            logger.error(f"Unexpected error during delete: {exc}")
            raise ConflictError(f"Failed to delete profile: {str(exc)}")
    
    def deactivate_profile(self, db: Session, profile_id: UUID) -> Profile:
        """
        Soft delete: deactivate a profile instead of deleting.
        This preserves data integrity and history.
        """
        profile = self.get(db, profile_id)
        profile.is_active = False
        db.commit()
        db.refresh(profile)
        return profile
    
    def activate_profile(self, db: Session, profile_id: UUID) -> Profile:
        """Reactivate a deactivated profile."""
        profile = self.get(db, profile_id)
        profile.is_active = True
        db.commit()
        db.refresh(profile)
        return profile

    def _ensure_batch_exists(self, db: Session, batch_id: UUID) -> None:
        from app.models.batch import Batch

        if db.get(Batch, batch_id) is None:
            raise ConflictError(f"Batch '{batch_id}' does not exist.")


profile_service = ProfileService()
