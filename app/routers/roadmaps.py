# app/routers/roadmaps.py

from uuid import UUID
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.roadmap import (
    RoadmapImportRequest, 
    RoadmapBulkImportResponse, 
    WeeklyRoadmapResponse, 
    WeeklyRoadmapShortResponse,
    RoadmapPreviewRequest,
    RoadmapPreviewResponse
)
from app.services.roadmap_service import roadmap_service

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])


@router.post("/import", response_model=RoadmapBulkImportResponse, status_code=status.HTTP_201_CREATED)
def import_roadmap(
    payload: RoadmapImportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "TECHNICAL_LEAD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Tech Leads can import roadmaps"
        )
    return roadmap_service.import_roadmap(db, payload, current_user.id)


@router.post("/preview", response_model=RoadmapPreviewResponse)
def preview_roadmap(
    payload: RoadmapPreviewRequest,
    current_user=Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "TECHNICAL_LEAD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Tech Leads can preview roadmaps"
        )
    entries = roadmap_service.preview_roadmap(payload.content)
    return {
        "entries": entries,
        "entries_count": len(entries)
    }


@router.get("", response_model=List[WeeklyRoadmapShortResponse])
def list_roadmaps(
    batch_id: Optional[UUID] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Enforce role-based filtering for interns
    if current_user.role == "INTERN":
        # Interns can only see roadmaps for their batch
        effective_batch_id = batch_id or current_user.batch_id
        if not effective_batch_id:
             return []
        
        # Interns should only see roadmaps for their role or global (role=None)
        # However, list_by_batch currently filters by a single role if provided.
        # We might need to adjust roadmap_service.list_by_batch to support multiple roles or handle global roadmaps.
        # For now, let's filter by the intern's role specifically.
        return roadmap_service.list_by_batch(db, effective_batch_id, current_user.intern_role)

    if batch_id:
        return roadmap_service.list_by_batch(db, batch_id, role)
    return roadmap_service.list(db)


@router.get("/{roadmap_id}", response_model=WeeklyRoadmapResponse)
def get_roadmap(
    roadmap_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    roadmap = roadmap_service.get_full(db, roadmap_id)
    # Permission check for Interns
    if current_user.role == "INTERN":
        if roadmap.batch_id != current_user.batch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access roadmaps from your own batch"
            )
        # Optional: strictly check role too?
        if roadmap.role and roadmap.role != current_user.intern_role:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access roadmaps for your specific role"
            )
    return roadmap


@router.delete("/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roadmap(
    roadmap_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in ["ADMIN", "TECHNICAL_LEAD"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins and Tech Leads can delete roadmaps"
        )
    roadmap_service.delete(db, roadmap_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
