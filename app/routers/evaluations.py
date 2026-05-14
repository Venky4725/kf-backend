# app/routers/evaluations.py

from uuid import UUID
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.evaluation import (
    EvaluationCreate, 
    EvaluationResponse, 
    EvaluationUpdate,
    EvaluationUpdateTechLead,
    EvaluationUpdateAdmin,
    EvaluationInternResponse
)
from app.services.evaluation_service import evaluation_service

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.get("/export")
def export_evaluations(
    intern_ids: str | None = None,
    week_numbers: str | None = None,
    batch_ids: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Export evaluations as CSV with filtering.
    - Tech Leads: All evaluations from their assigned batches (batch-based access)
    - Admins: All evaluations
    
    Query params:
    - intern_ids: Comma-separated UUIDs (e.g., "uuid1,uuid2")
    - week_numbers: Comma-separated integers (e.g., "1,2,3")
    - batch_ids: Comma-separated UUIDs (e.g., "uuid1,uuid2")
    """
    import csv
    import logging
    from io import StringIO
    from fastapi.responses import StreamingResponse
    from app.models.evaluation import Evaluation
    from app.models.profile import Profile
    from app.models.batch import Batch
    
    logger = logging.getLogger(__name__)
    logger.info(f"CSV export initiated by user: {current_user.id} ({current_user.role})")
    
    try:
        # Base query with joins
        query = db.query(Evaluation).join(
            Profile, Evaluation.intern_id == Profile.id
        ).outerjoin(
            Batch, Profile.batch_id == Batch.id
        )
        
        # CRITICAL: Tech Lead can export ALL evaluations from their assigned batches (batch-based access)
        if current_user.role == "TECHNICAL_LEAD":
            from app.core.tech_lead_utils import get_tech_lead_batch_ids
            tl_batch_ids = get_tech_lead_batch_ids(db, current_user.id)
            if tl_batch_ids:
                query = query.filter(Profile.batch_id.in_(tl_batch_ids))
                logger.info(f"Tech Lead filter applied: batch_ids={tl_batch_ids}")
            else:
                # Tech lead has no batches assigned, export nothing
                query = query.filter(Profile.id == None)
                logger.info("Tech Lead has no assigned batches, exporting no evaluations")
        
        # Apply intern_ids filter
        if intern_ids and intern_ids.strip():
            try:
                intern_uuid_list = [UUID(id.strip()) for id in intern_ids.split(",") if id.strip()]
                if intern_uuid_list:
                    query = query.filter(Evaluation.intern_id.in_(intern_uuid_list))
                    logger.info(f"Filtered by intern_ids: {len(intern_uuid_list)} interns")
            except ValueError as e:
                logger.warning(f"Invalid intern_ids format: {e}")
                # Continue without this filter
        
        # Apply week_numbers filter
        if week_numbers and week_numbers.strip():
            try:
                week_list = [int(w.strip()) for w in week_numbers.split(",") if w.strip()]
                if week_list:
                    query = query.filter(Evaluation.week_number.in_(week_list))
                    logger.info(f"Filtered by week_numbers: {week_list}")
            except ValueError as e:
                logger.warning(f"Invalid week_numbers format: {e}")
                # Continue without this filter
        
        # Apply batch_ids filter
        if batch_ids and batch_ids.strip():
            try:
                batch_uuid_list = [UUID(id.strip()) for id in batch_ids.split(",") if id.strip()]
                if batch_uuid_list:
                    query = query.filter(Profile.batch_id.in_(batch_uuid_list))
                    logger.info(f"Filtered by batch_ids: {len(batch_uuid_list)} batches")
            except ValueError as e:
                logger.warning(f"Invalid batch_ids format: {e}")
                # Continue without this filter
        
        # Order by week and date
        query = query.order_by(Evaluation.week_number.asc(), Evaluation.created_at.desc())
        
        # Execute query
        evaluations = query.all()
        logger.info(f"Found {len(evaluations)} evaluations to export")
        
        # Generate CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Intern Name",
            "Intern Email",
            "Batch",
            "Week Number",
            "Score",
            "Feedback",
            "Reviewed By",
            "Date"
        ])
        
        # Write data rows
        for evaluation in evaluations:
            # Get intern profile
            intern = db.get(Profile, evaluation.intern_id)
            reviewer = db.get(Profile, evaluation.reviewed_by)
            
            # Get batch name (handle null batch)
            batch_name = ""
            if intern and intern.batch_id:
                batch = db.get(Batch, intern.batch_id)
                batch_name = batch.name if batch else ""
            
            writer.writerow([
                intern.name if intern else "Unknown",
                intern.email if intern else "",
                batch_name,
                evaluation.week_number,
                evaluation.score,
                evaluation.feedback or "",
                reviewer.name if reviewer else "Unknown",
                evaluation.created_at.strftime("%Y-%m-%d %H:%M:%S") if evaluation.created_at else ""
            ])
        
        # Prepare response
        output.seek(0)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluations_export_{timestamp}.csv"
        
        logger.info(f"CSV export complete: {len(evaluations)} rows")
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error exporting evaluations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export evaluations: {str(e)}"
        )


@router.get("", response_model=Union[list[EvaluationResponse], list[EvaluationInternResponse]])
def get_evaluations(
    skip: int = 0,
    limit: int = 100,
    intern_id: UUID | None = None,
    reviewed_by: UUID | None = None,
    week_number: int | None = None,
    search: str | None = None,
    batch_id: UUID | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    score_min: float | None = None,
    score_max: float | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get evaluations with role-based filtering, searching, and sorting.
    
    Query Parameters:
    - skip: Pagination offset (default: 0)
    - limit: Max results per page (default: 100)
    - intern_id: Filter by specific intern UUID
    - reviewed_by: Filter by specific reviewer UUID
    - week_number: Filter by specific week number
    - batch_id: Filter by specific batch UUID
    - score_min: Filter by minimum score (0-5)
    - score_max: Filter by maximum score (0-5)
    - search: Search in intern name, feedback (partial match)
    - sort_by: Sort field (week_number, score, created_at, updated_at, intern_name)
    - order: Sort order (asc, desc) - default: desc
    
    RBAC:
    - INTERN: Cannot see scores (only feedback)
    - TECHNICAL_LEAD: Can only see evaluations for interns in their assigned batches
    - ADMIN: Can see all evaluations
    """
    evaluations = evaluation_service.list_evaluations(
        db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        intern_id=intern_id,
        reviewed_by=reviewed_by,
        week_number=week_number,
        search=search,
        batch_id=batch_id,
        sort_by=sort_by,
        order=order,
        score_min=score_min,
        score_max=score_max,
    )
    
    # Return different response based on role
    if current_user.role == "INTERN":
        # Interns should not see scores
        return [EvaluationInternResponse.model_validate(e) for e in evaluations]
    else:
        # Tech Leads and Admins can see full data including scores
        return [EvaluationResponse.model_validate(e) for e in evaluations]


@router.get("/{evaluation_id}", response_model=Union[EvaluationResponse, EvaluationInternResponse])
def get_evaluation(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get single evaluation with role-based filtering.
    - INTERN: Cannot see score
    - TECH_LEAD/ADMIN: Can see all fields including score
    """
    evaluation = evaluation_service.get(db, evaluation_id)
    
    # Return different response based on role
    if current_user.role == "INTERN":
        return EvaluationInternResponse.model_validate(evaluation)
    else:
        return EvaluationResponse.model_validate(evaluation)


@router.post("", response_model=EvaluationResponse, status_code=status.HTTP_201_CREATED)
def create_evaluation(
    payload: EvaluationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return evaluation_service.create_evaluation(db, payload, current_user)


@router.put("/{evaluation_id}", response_model=EvaluationResponse)
def update_evaluation(
    evaluation_id: UUID,
    payload: EvaluationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Update evaluation with role-based field restrictions.
    
    ADMIN: Can update all fields (week_number, score, feedback, intern_id, reviewed_by)
    TECHNICAL_LEAD: Can only update week_number, score, feedback for evaluations in their assigned batches
    
    Security: All restrictions enforced server-side. Direct API manipulation attempts will fail.
    """
    # Role-based schema enforcement happens at service layer
    # The payload accepts all fields but service layer filters based on role
    return evaluation_service.update_evaluation(db, evaluation_id, payload, current_user)


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evaluation(
    evaluation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """
    Delete evaluation with role-based authorization.
    
    ADMIN: Can delete any evaluation
    TECHNICAL_LEAD: Can only delete evaluations for interns in their assigned batches
    
    Security: All restrictions enforced server-side. Direct API manipulation attempts will fail.
    """
    evaluation_service.delete(db, evaluation_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
