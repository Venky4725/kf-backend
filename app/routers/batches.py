# app/routers/batches.py

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.services.batch_service import batch_service

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.get("", response_model=list[BatchResponse])
def get_batches(
    skip: int = 0,
    limit: int = 100,
    tech_lead_id: UUID | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get batches with optional filtering.
    
    Returns enriched batch data including tech lead names for display.
    
    Query Parameters:
    - tech_lead_id: Filter batches where the tech lead is assigned (first or second)
    
    RBAC:
    - TECHNICAL_LEAD: Automatically filtered to only their assigned batches
    - ADMIN: Can see all batches
    """
    # Tech Lead can only see their assigned batches
    if current_user.role == "TECHNICAL_LEAD":
        tech_lead_id = current_user.id
    
    # Service returns list of dicts with enriched data
    return batch_service.list_batches(
        db,
        skip=skip,
        limit=limit,
        tech_lead_id=tech_lead_id,
        search=search,
        sort_by=sort_by,
        order=order,
    )


@router.get("/available-for-evaluations", response_model=list[BatchResponse])
def get_available_batches_for_evaluations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get distinct batches available for evaluations dropdown.
    - Admin: All batches
    - Tech Lead: Only assigned batches
    """
    tech_lead_id = None
    if current_user.role == "TECHNICAL_LEAD":
        tech_lead_id = current_user.id
    
    # Use list_batches with high limit to get all relevant batches
    return batch_service.list_batches(
        db,
        limit=500,  # High limit to ensure all batches are returned for dropdown
        tech_lead_id=tech_lead_id,
        sort_by="name",
        order="asc"
    )


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a single batch with enriched tech lead information.
    Returns the same structure as list endpoint for consistency.
    """
    batch = batch_service.get(db, batch_id)
    # Enrich with tech lead information for consistent response
    return batch_service._enrich_batch_response(db, batch)


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
):
    """Create a new batch with enriched response."""
    batch = batch_service.create_batch(db, payload)
    # Enrich with tech lead information for consistent response
    return batch_service._enrich_batch_response(db, batch)


@router.put("/{batch_id}", response_model=BatchResponse)
def update_batch(
    batch_id: UUID,
    payload: BatchUpdate,
    db: Session = Depends(get_db),
):
    """Update a batch with enriched response and debug logging."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the update request
    logger.info(f"Updating batch {batch_id} with payload: {payload.model_dump(exclude_unset=True)}")
    
    # Update the batch
    batch = batch_service.update_batch(db, batch_id, payload)
    
    # Log what was saved
    logger.info(f"Batch updated - first_tech_lead_id: {batch.first_tech_lead_id}, second_tech_lead_id: {batch.second_tech_lead_id}, third_tech_lead_id: {getattr(batch, 'third_tech_lead_id', None)}")
    
    # Refresh batch to make sure we're getting fresh data for enrichment 
    db.refresh(batch)
    
    # Enrich with tech lead information for consistent response
    enriched = batch_service._enrich_batch_response(db, batch)
    
    # Log the enriched response
    logger.info(f"Enriched response - tech_leads_display: {enriched['tech_leads_display']}")
    
    return enriched


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    batch_service.delete(db, batch_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
